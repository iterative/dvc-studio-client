from typing import List, Optional, TypedDict
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter

from . import logger

AVAILABLE_SCOPES = ["live", "dvc_experiment", "view_url", "dql", "download_model"]


class DeviceLoginResponse(TypedDict):
    device_code: str
    user_code: str
    verification_uri: str
    token_uri: str
    token_name: str
    expires_in: int


class StudioAuthError(Exception):
    pass


class InvalidScopesError(StudioAuthError):
    pass


class AuthorizationExpired(StudioAuthError):
    pass


def initiate_authorization(*, name, hostname, scopes, use_device_code=False):
    """Initiate Authorization

    This method initiates the authorization process for a client application.
    It generates a user code and a verification URI that the user needs to
    access in order to authorize the application.

    Parameters:
        name (str): The name of the client application.
        hostname (str): The base URL of the application.
        scopes (str): A comma-separated string of scopes that the application requires.
        use_device_code (bool, optional): Whether to use the device code
        flow for authorization. Default is False.

    Returns:
        tuple: A tuple containing the token name and the access token.
        The token name is a string representing the token's name,
        while the access token is a string representing the authorized access token.
    """

    import webbrowser

    response = start_device_login(
        client_name="dvc",
        base_url=hostname,
        token_name=name,
        scopes=scopes.split(","),
    )
    verification_uri = response["verification_uri"]
    user_code = response["user_code"]
    device_code = response["device_code"]
    token_uri = response["token_uri"]
    token_name = response["token_name"]

    opened = False
    if not use_device_code:
        print(
            f"A web browser has been opened at \n{verification_uri}.\n"
            f"Please continue the login in the web browser.\n"
            f"If no web browser is available or if the web browser fails to open,\n"
            f"use device code flow with `dvc studio login --use-device-code`."
        )
        url = f"{verification_uri}?code={user_code}"
        opened = webbrowser.open(url)

    if not opened:
        print(f"Please open the following url in your browser.\n{verification_uri}")
        print(f"And enter the user code below {user_code} to authorize.")

    access_token = check_token_authorization(uri=token_uri, device_code=device_code)

    return token_name, access_token


def start_device_login(
    *,
    client_name: str,
    base_url: str = None,
    token_name: Optional[str] = None,
    scopes: Optional[List[str]] = None,
) -> DeviceLoginResponse:
    """

    This method starts the device login process for Studio.

    Parameters:
    - client_name (required): The name of the client application.

    Optional Parameters:
    - base_url: The base URL of the Studio API.
        If not provided, the default value is "https://studio.iterative.ai".
    - token_name: The name of the token. If not provided, it defaults to None.
    - scopes: A list of scopes to request. If not provided, it defaults to None.

    Returns:
    - DeviceLoginResponse: A response object containing the device login information.

    Raises:
    - ValueError: If any of the provided scopes are not valid.
    - RequestException: If the request fails with any 400 response or any other reason.

    """
    logger.debug(
        "Starting device login for Studio%s",
        f" ({base_url})" if base_url else "",
    )
    if invalid_scopes := list(filter(lambda s: s not in AVAILABLE_SCOPES, scopes)):
        raise InvalidScopesError(
            f"Following scopes are not valid: {', '.join(invalid_scopes)}"
        )

    body = {"client_name": client_name}

    if token_name:
        body["token_name"] = token_name

    if scopes:
        body["scopes"] = scopes

    logger.debug(f"JSON body `{body=}`")

    response = requests.post(
        url=urljoin(base_url or "https://studio.iterative.ai", "api/device-login"),
        json=body,
        headers={
            "Content-type": "application/json",
        },
        timeout=5,
    )

    response.raise_for_status()
    d = response.json()

    logger.debug("received response: %s (status=%r)", d, response.status_code)
    return d


def check_token_authorization(*, uri: str, device_code: str) -> Optional[str]:
    """
    Checks the authorization status of a token based on a device code and
    returns access token upon successful authorization.

    Parameters:
    - uri (str): The token uri to send the request to.
    - device_code (str): The device code to check authorization for.

    Returns:
    - str | None: The access token if authorized, otherwise None.

    Raises:
    - requests.HTTPError: If the status code of the response is not 200.

    Example Usage:
    ```
    token = check_token_authorization(
        uri="https://example.com/api/", device_code="1234567890"
    )
    if token is not None:
        print("Access token:", token)
    else:
        print("Authorization expired.")
    ```
    """
    import time

    logger.debug("Polling to find if the user code is authorized")

    data = {"code": device_code}
    session = requests.Session()
    session.mount(uri, HTTPAdapter(max_retries=3))

    logger.debug("Checking with %s to %s", device_code, uri)

    counter = 1
    while True:
        logger.debug("Polling attempt #%s", counter)
        r = session.post(uri, json=data, timeout=5, allow_redirects=False)
        counter += 1
        if r.status_code == 400:
            d = r.json()
            detail = d.get("detail")
            if detail == "authorization_pending":
                # Wait 5 seconds before retrying.
                time.sleep(5)
                continue
            if detail == "authorization_expired":
                raise AuthorizationExpired(
                    "failed to authenticate: This 'device_code' has expired."
                )

        r.raise_for_status()

        return r.json()["access_token"]
