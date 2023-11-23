import pytest
import requests
from requests import Response

from dvc_studio_client.auth import (
    AuthorizationExpired,
    DeviceLoginResponse,
    check_token_authorization,
    start_device_login,
)


def test_start_device_login(mocker):
    example_response = {
        "device_code": "random-device-code",
        "user_code": "MOCKCODE",
        "verification_uri": "http://example.com/verify",
        "token_uri": "http://example.com/token",
        "token_name": "token_name",
        "expires_in": 1500,
    }
    mock_post = mocker.patch(
        "requests.post",
        return_value=mock_response(mocker, 200, example_response),
    )

    response: DeviceLoginResponse = start_device_login(
        base_url="https://example.com",
        client_name="dvc",
        token_name="token_name",
        scopes=["live"],
    )

    assert mock_post.called
    assert mock_post.call_args == mocker.call(
        url="https://example.com/api/device-login",
        json={"client_name": "dvc", "token_name": "token_name", "scopes": ["live"]},
        headers={"Content-type": "application/json"},
        timeout=5,
    )
    assert response == example_response


def test_check_token_authorization_expired(mocker):
    mocker.patch("time.sleep")
    mock_post = mocker.patch(
        "requests.Session.post",
        side_effect=[
            mock_response(mocker, 400, {"detail": "authorization_pending"}),
            mock_response(mocker, 400, {"detail": "authorization_expired"}),
        ],
    )

    with pytest.raises(AuthorizationExpired):
        check_token_authorization(
            uri="https://example.com/token_uri", device_code="random_device_code"
        )

    assert mock_post.call_count == 2
    assert mock_post.call_args == mocker.call(
        "https://example.com/token_uri",
        json={"code": "random_device_code"},
        timeout=5,
        allow_redirects=False,
    )


def test_check_token_authorization_error(mocker):
    mocker.patch("time.sleep")
    mock_post = mocker.patch(
        "requests.Session.post",
        side_effect=[
            mock_response(mocker, 400, {"detail": "authorization_pending"}),
            mock_response(mocker, 500, {"detail": "unexpected_error"}),
        ],
    )

    with pytest.raises(requests.RequestException):
        check_token_authorization(
            uri="https://example.com/token_uri", device_code="random_device_code"
        )

    assert mock_post.call_count == 2
    assert mock_post.call_args == mocker.call(
        "https://example.com/token_uri",
        json={"code": "random_device_code"},
        timeout=5,
        allow_redirects=False,
    )


def test_check_token_authorization_success(mocker):
    mocker.patch("time.sleep")
    mock_post = mocker.patch(
        "requests.Session.post",
        side_effect=[
            mock_response(mocker, 400, {"detail": "authorization_pending"}),
            mock_response(mocker, 400, {"detail": "authorization_pending"}),
            mock_response(mocker, 200, {"access_token": "isat_token"}),
        ],
    )

    assert (
        check_token_authorization(
            uri="https://example.com/token_uri", device_code="random_device_code"
        )
        == "isat_token"
    )

    assert mock_post.call_count == 3
    assert mock_post.call_args == mocker.call(
        "https://example.com/token_uri",
        json={"code": "random_device_code"},
        timeout=5,
        allow_redirects=False,
    )


def mock_response(mocker, status_code, json):
    response = Response()
    response.status_code = status_code
    mocker.patch.object(response, "json", side_effect=[json])

    return response
