import logging

import pytest
from requests import RequestException

from dvc_studio_client.env import STUDIO_ENDPOINT, STUDIO_REPO_URL, STUDIO_TOKEN
from dvc_studio_client.post_live_metrics import (
    VALID_URLS,
    _convert_to_studio_url,
    _get_remote_url,
    get_studio_repo_url,
    get_studio_token_and_repo_url,
    post_live_metrics,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://github.com/USERNAME/REPOSITORY.git",
            "github:USERNAME/REPOSITORY",
        ),
        (
            "https://gitlab.com/USERNAME/REPOSITORY",
            "gitlab:USERNAME/REPOSITORY",
        ),
        (
            "https://bitbucket.org/USERNAME/REPOSITORY",
            "bitbucket:USERNAME/REPOSITORY",
        ),
        (
            "git@github.com:USERNAME/REPOSITORY.git",
            "github:USERNAME/REPOSITORY",
        ),
        (
            "git@gitlab.com:USERNAME/REPOSITORY.git",
            "gitlab:USERNAME/REPOSITORY",
        ),
        (
            "git@bitbucket.org:USERNAME/REPOSITORY.git",
            "bitbucket:USERNAME/REPOSITORY",
        ),
    ],
)
def test_convert_to_studio_url(url, expected):
    assert _convert_to_studio_url(url) == expected


def test_get_remote_url(tmpdir):
    from git import Repo

    repo = Repo.clone_from("https://github.com/iterative/dvclive.git", tmpdir)
    assert _get_remote_url(repo) == "https://github.com/iterative/dvclive.git"


def test_get_studio_repo_url(caplog, mocker):
    caplog.set_level(logging.DEBUG)

    from git.exc import GitError

    mocker.patch(
        "dvc_studio_client.post_live_metrics._get_remote_url",
        side_effect=GitError(),
    )
    caplog.clear()
    get_studio_repo_url()
    assert caplog.records[0].message == (
        "Tried to find remote url for the active branch but failed.\n"
    )
    assert caplog.records[1].message == (
        "Couldn't find a valid Studio Repo URL.\n"
        "You can try manually setting the environment variable "
        f"`{STUDIO_REPO_URL}`."
    )

    mocker.patch(
        "dvc_studio_client.post_live_metrics._get_remote_url",
        return_value="bad@repo:url",
    )
    caplog.clear()
    get_studio_repo_url()
    assert caplog.records[0].message == (
        "Found invalid remote url for the active branch.\n"
        f" Supported urls must start with any of {VALID_URLS}"
    )
    assert caplog.records[1].message == (
        "Couldn't find a valid Studio Repo URL.\n"
        "You can try manually setting the environment variable "
        f"`{STUDIO_REPO_URL}`."
    )


def test_post_live_metrics_skip_on_missing_token(caplog):
    caplog.set_level(logging.DEBUG)
    assert post_live_metrics("start", "current_rev", "fooname", "fooclient") is None
    assert caplog.records[0].message == (
        "STUDIO_TOKEN not found. Skipping `post_studio_live_metrics`"
    )


def test_post_live_metrics_skip_on_schema_error(caplog, monkeypatch):
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    caplog.set_level(logging.DEBUG)

    assert post_live_metrics("start", "bad_hash", "fooname", "fooclient") is None
    assert caplog.records[0].message == (
        "expected a length 40 commit sha for dictionary value @ "
        "data['baseline_sha']. Got 'bad_hash'"
    )


def test_post_live_metrics_start_event(mocker, caplog, monkeypatch):
    monkeypatch.setenv(STUDIO_ENDPOINT, "https://0.0.0.0")
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    caplog.set_level(logging.DEBUG)

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0",
        json={
            "type": "start",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )

    post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
        params={"params.yaml": {"foo": "bar"}},
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0",
        json={
            "type": "start",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "params": {"params.yaml": {"foo": "bar"}},
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )


def test_post_live_metrics_data_skip_if_no_step(mocker, caplog, monkeypatch):
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    caplog.set_level(logging.DEBUG)

    assert post_live_metrics("data", "f" * 40, "fooname", "fooclient") is None
    assert caplog.records[0].message == ("Missing `step` in `data` event.")


def test_post_live_metrics_data(mocker, caplog, monkeypatch):
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    caplog.set_level(logging.DEBUG)

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics("data", "f" * 40, "fooname", "fooclient", step=0)
    mocked_post.assert_called_with(
        "https://studio.iterative.ai/api/live",
        json={
            "type": "data",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "step": 0,
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )

    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots={"dvclive/plots/metrics/foo.tsv": {"data": [{"step": 0, "foo": 1.0}]}},
    )
    mocked_post.assert_called_with(
        "https://studio.iterative.ai/api/live",
        json={
            "type": "data",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "step": 0,
            "metrics": {"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
            "plots": {
                "dvclive/plots/metrics/foo.tsv": {"data": [{"step": 0, "foo": 1.0}]}
            },
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )


def test_post_live_metrics_done(mocker, caplog, monkeypatch):
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    caplog.set_level(logging.DEBUG)

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        "done",
        "f" * 40,
        "fooname",
        "fooclient",
    )
    mocked_post.assert_called_with(
        "https://studio.iterative.ai/api/live",
        json={
            "type": "done",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )

    assert post_live_metrics(
        "done", "f" * 40, "fooname", "fooclient", experiment_rev="h" * 40
    )
    mocked_post.assert_called_with(
        "https://studio.iterative.ai/api/live",
        json={
            "type": "done",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "experiment_rev": "h" * 40,
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=5,
    )


def test_post_live_metrics_bad_response(mocker, monkeypatch):
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 400
    mocker.patch("requests.post", return_value=mocked_response)
    assert (
        post_live_metrics(
            "start",
            "f" * 40,
            "fooname",
            "fooclient",
        )
        is False
    )

    mocker.patch("requests.post", side_effect=RequestException())
    assert (
        post_live_metrics(
            "start",
            "f" * 40,
            "fooname",
            "fooclient",
        )
        is False
    )


def test_get_studio_token_and_repo_url_skip_repo_url(monkeypatch):
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    token, repo_url = get_studio_token_and_repo_url()
    assert token is None
    assert repo_url is None  # Skipped call to get_repo_url
