import logging
import re
from functools import lru_cache
from os import getenv
from typing import Any, Dict, Literal, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import RequestException
from voluptuous import Invalid, MultipleInvalid
from voluptuous.humanize import humanize_error

from .env import (
    DVC_STUDIO_CLIENT_LOGLEVEL,
    DVC_STUDIO_OFFLINE,
    DVC_STUDIO_REPO_URL,
    DVC_STUDIO_TOKEN,
    DVC_STUDIO_URL,
    DVCLIVE_LOGLEVEL,
    STUDIO_ENDPOINT,
    STUDIO_REPO_URL,
    STUDIO_TOKEN,
)
from .schema import SCHEMAS_BY_TYPE

STUDIO_URL = "https://studio.iterative.ai"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(
    getenv(DVC_STUDIO_CLIENT_LOGLEVEL, getenv(DVCLIVE_LOGLEVEL, "WARNING")).upper()
)


def _get_remote_url() -> str:
    from dulwich.porcelain import get_remote_repo
    from dulwich.repo import Repo

    with Repo.discover() as repo:
        try:
            _remote, url = get_remote_repo(repo)
        except IndexError:
            # IndexError happens when the head is detached
            _remote, url = get_remote_repo(repo, b"origin")
        return url


@lru_cache(maxsize=1)
def get_studio_repo_url() -> Optional[str]:
    from dulwich.errors import NotGitRepository

    try:
        return _get_remote_url()
    except NotGitRepository:
        logger.warning(
            "Couldn't find a valid Studio Repo URL.\n"
            "You can try manually setting the environment variable `%s`.",
            STUDIO_REPO_URL,
        )
        return None


def get_studio_token_and_repo_url(studio_token=None, studio_repo_url=None):
    studio_token = studio_token or getenv(DVC_STUDIO_TOKEN) or getenv(STUDIO_TOKEN)
    """Get studio token and repo_url. Kept for backwards compatibility."""
    config = get_studio_config(
        studio_token=studio_token, studio_repo_url=studio_repo_url
    )
    return config.get("token"), config.get("repo_url")


def get_studio_config(
    dvc_studio_config: Optional[Dict[str, Any]] = None,
    offline: bool = False,
    studio_token: Optional[str] = None,
    studio_repo_url: Optional[str] = None,
    studio_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Get studio config options.

    Args:
        dvc_studio_config (Optional[dict]): Dict returned by dvc.Repo.config["studio"].
        offline (bool): Whether offline mode is enabled. Default: false.
        studio_token (Optional[str]): Studio access token obtained from the UI.
        studio_repo_url (Optional[str]): URL of the Git repository that has been
            imported into Studio UI.
        studio_url (Optional[str]): Base URL of Studio UI (if self-hosted).
    Returns:
        Dict:
            Config options for posting live metrics.
            Keys match the DVC studio config section.
            Example:
                {
                    "token": "mytoken",
                    "repo_url": "git@github.com:iterative/dvc-studio-client.git",
                    "url": "https://studio.iterative.ai",
                }
    """

    config = {}
    if not dvc_studio_config:
        dvc_studio_config = {}

    def to_bool(var):
        if var is None:
            return False
        return bool(re.search("1|y|yes|true", str(var), flags=re.I))

    offline = (
        offline
        or to_bool(getenv(DVC_STUDIO_OFFLINE))
        or to_bool(dvc_studio_config.get("offline"))
    )
    if offline:
        logger.debug("Offline mode enabled. Skipping `post_studio_live_metrics`")
        return {}

    studio_token = (
        studio_token
        or getenv(DVC_STUDIO_TOKEN)
        or getenv(STUDIO_TOKEN)
        or dvc_studio_config.get("token")
    )
    if not studio_token:
        logger.debug(
            f"{DVC_STUDIO_TOKEN} not found. Skipping `post_studio_live_metrics`"
        )
        return {}
    config["token"] = studio_token

    studio_repo_url = (
        studio_repo_url
        or getenv(DVC_STUDIO_REPO_URL)
        or getenv(STUDIO_REPO_URL)
        or dvc_studio_config.get("repo_url")
    )
    if studio_repo_url is None:
        logger.debug(
            f"{DVC_STUDIO_REPO_URL} not found. Trying to automatically find it."
        )
        studio_repo_url = get_studio_repo_url()
    if studio_repo_url:
        config["repo_url"] = studio_repo_url
    else:
        logger.debug(
            f"{DVC_STUDIO_REPO_URL} not found. Skipping `post_studio_live_metrics`"
        )
        return {}

    studio_url = studio_url or getenv(DVC_STUDIO_URL) or dvc_studio_config.get("url")
    if studio_url:
        config["url"] = studio_url
    else:
        logger.debug(f"{DVC_STUDIO_URL} not found. Using {STUDIO_URL}.")
        config["url"] = STUDIO_URL

    return config


def post_live_metrics(  # noqa: C901
    event_type: Literal["start", "data", "done"],
    baseline_sha: str,
    name: str,
    client: Literal["dvc", "dvclive"],
    experiment_rev: Optional[str] = None,
    machine: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    plots: Optional[Dict[str, Any]] = None,
    step: Optional[int] = None,
    dvc_studio_config: Optional[Dict[str, Any]] = None,
    offline: bool = False,
    studio_token: Optional[str] = None,
    studio_repo_url: Optional[str] = None,
    studio_url: Optional[str] = None,
) -> Optional[bool]:
    """Post `event_type` to Studio's `api/live`.

    Requires the environment variable `DVC_STUDIO_TOKEN` to be set.
    If the environment variable `DVC_STUDIO_REPO_URL` is not set, will attempt to
    infer it from `git ls-remote --get-url`.

    Args:
        event_type (Literal["start", "data", "done"]): Type of the event.
        baseline_sha (str): SHA of the commit from which the experiment starts.
        name (str): Name of the experiment.
            Automatically generated by DVC(Live) or manually passed by the user.
            (baseline_sha, name) is a unique identifier of the experiment.
        client (Literal["dvc", "dvclive"]): Name of the client.
        experiment_rev (Optional[str]): SHA of the revision created for
            the experiment.
            Only used when `event_type="done"`.
            Only used when
        machine (Optional[Dict[str, Any]]): Information about the machine
            running the experiment.
            Defaults to `None`.
            ```
            machine={
                "cpu": 0.94
                "memory": 0.99
                "cloud": "aws"
                "instance": "t2.micro"
            }
            ```
        message: (Optional[str]): Custom message to be displayed as the commit
            message in Studio UI.
        metrics (Optional[Dict[str, Any]]): Updates to DVC metric files.
            Defaults to `None`.
            Only used when `event_type="data"`.
            ```
            metrics={
                "dvclive/metrics.json": {
                    "data": {
                        "foo": 1.0
                    }
                }
            }
            ```
        params (Optional[Dict[str, Any]]): Updates to DVC param files.
            Defaults to `None`.
            ```
            params={
                "dvclive/params.yaml": {
                    "foo": "bar"
                }
            }
            ```
        plots (Optional[Dict[str, Any]]): Updates to DVC plots files.
            Defaults to `None`.
            Only used when `event_type="data"`.
            ```
            plots={
                "dvclive/plots/metrics/foo.tsv": {
                    "data": [{"step": 0, "foo": 1.0}]
                }
            }
            ```
        step (Optional[int]): Current step of the training loop.
            Usually comes from DVCLive `Live.step` property.
            Required in when `event_type="data"`.
            Defaults to `None`.
        dvc_studio_config (Optional[Dict]): DVC config options for Studio.
        offline (bool): Whether offline mode is enabled.
        studio_token (Optional[str]): Studio access token obtained from the UI.
        studio_repo_url (Optional[str]): URL of the Git repository that has been
            imported into Studio UI.
        studio_url (Optional[str]): Base URL of Studio UI (if self-hosted).
    Returns:
        Optional[bool]:
            `True` - if received status code 200 from Studio.
            `False` - if received other status code or RequestException raised.
            `None`- if prerequisites weren't met and the request was not sent.
    """
    config = get_studio_config(
        dvc_studio_config=dvc_studio_config,
        offline=offline,
        studio_token=studio_token,
        studio_repo_url=studio_repo_url,
        studio_url=studio_url,
    )

    if not config:
        return None

    body = {
        "type": event_type,
        "repo_url": config["repo_url"],
        "baseline_sha": baseline_sha,
        "name": name,
        "client": client,
    }

    if params:
        body["params"] = params

    if metrics:
        body["metrics"] = metrics

    if machine:
        body["machine"] = machine

    if event_type == "start":
        if message:
            # Cutting the message to match the commit title length limit.
            body["message"] = message[:72]
    elif event_type == "data":
        if step is None:
            logger.warning("Missing `step` in `data` event.")
            return None
        body["step"] = step
        if plots:
            body["plots"] = plots

    elif event_type == "done":
        if experiment_rev:
            body["experiment_rev"] = experiment_rev

    elif event_type != "start":
        logger.warning(f"Invalid `event_type`: {event_type}")
        return None

    try:
        SCHEMAS_BY_TYPE[event_type](body)
    except (Invalid, MultipleInvalid) as e:
        logger.warning(humanize_error(body, e))
        return None

    logger.debug(f"post_studio_live_metrics `{event_type=}`")
    logger.debug(f"JSON body `{body=}`")

    path = getenv(STUDIO_ENDPOINT) or "api/live"
    url = urljoin(config["url"], path)
    try:
        response = requests.post(
            url,
            json=body,
            headers={
                "Content-type": "application/json",
                "Authorization": f"token {config['token']}",
            },
            timeout=(30, 5),
        )
    except RequestException as e:
        logger.warning(f"Failed to post to Studio: {e}")
        return False

    message = response.content.decode()
    logger.debug(
        f"post_to_studio: {response.status_code=}" f", {message=}" if message else ""
    )

    if response.status_code != 200:
        logger.warning(f"Failed to post to Studio: {message}")
        return False

    return True
