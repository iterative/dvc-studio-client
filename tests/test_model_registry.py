import pytest

from dvc_studio_client.env import DVC_STUDIO_TOKEN, DVC_STUDIO_URL
from dvc_studio_client.model_registry import get_download_uris


@pytest.fixture(autouse=True)
def setenv(monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_URL, "https://0.0.0.0")
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")


def test_get_download_uris(mocker, monkeypatch):
    expected = {
        "model1": "http://foo/model",
        "dir/model2": "http://foo/model2",
    }
    mocked_get = mocker.patch(
        "requests.get",
        return_value=mocker.MagicMock(
            status_code=200,
            json=mocker.Mock(return_value=expected),
        ),
    )
    assert get_download_uris("https://my/repo.git", "model") == expected
    mocked_get.assert_called_with(
        "https://0.0.0.0/api/model-registry/get-download-uris",
        params={
            "repo": "https://my/repo.git",
            "name": "model",
        },
        headers={"Authorization": "token FOO_TOKEN"},
        timeout=(30, 5),
    )


def test_get_download_uris_args(mocker):
    mocked_get = mocker.patch(
        "requests.get", return_value=mocker.MagicMock(status_code=200)
    )
    with pytest.raises(ValueError):
        get_download_uris(
            "https://my/repo.git", "model", version="version", stage="stage"
        )

    mocked_get.reset_mock()
    get_download_uris("https://my/repo.git", "model", version="version")
    assert mocked_get.call_args.kwargs["params"].get("version") == "version"

    mocked_get.reset_mock()
    get_download_uris("https://my/repo.git", "model", stage="stage")
    assert mocked_get.call_args.kwargs["params"].get("stage") == "stage"
