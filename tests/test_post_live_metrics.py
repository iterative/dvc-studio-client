import logging
from copy import deepcopy
from unittest.mock import DEFAULT, MagicMock

import pytest
from dvc_studio_client import DEFAULT_STUDIO_URL
from dvc_studio_client.env import (
    DVC_STUDIO_REPO_URL,
    DVC_STUDIO_TOKEN,
    DVC_STUDIO_URL,
    STUDIO_REPO_URL,
    STUDIO_TOKEN,
)
from dvc_studio_client.post_live_metrics import (
    MAX_NUMBER_OF_PLOTS,
    get_studio_token_and_repo_url,
    post_live_metrics,
)
from requests import RequestException


def test_post_live_metrics_skip_on_missing_token(caplog):
    with caplog.at_level(logging.DEBUG, logger="dvc_studio_client"):
        assert post_live_metrics("start", "current_rev", "fooname", "fooclient") is None
        assert caplog.records[0].message == (
            "DVC_STUDIO_TOKEN not found. Skipping `post_studio_live_metrics`"
        )


def test_post_live_metrics_skip_on_schema_error(caplog, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(DVC_STUDIO_REPO_URL, "FOO_REPO_URL")
    monkeypatch.setenv(DVC_STUDIO_URL, DEFAULT_STUDIO_URL)
    with caplog.at_level(logging.DEBUG, logger="dvc_studio_client"):
        assert post_live_metrics("start", "bad_hash", "fooname", "fooclient") is None
        assert caplog.records[0].message == (
            "expected a length 40 commit sha for dictionary value @ "
            "data['baseline_sha']. Got 'bad_hash'"
        )


def test_post_live_metrics_start_event(mocker, monkeypatch):
    repo_url = "FOO_REPO_URL"
    studio_url = "https://0.0.0.0"
    studio_token = "FOO_TOKEN"
    baseline_sha = "f" * 40
    event_type = "start"
    name = "fooname"
    client = "fooclient"

    post_url = f"{studio_url}/api/live"
    headers = {
        "Authorization": f"token {studio_token}",
        "Content-type": "application/json",
    }
    base_event = {
        "type": "start",
        "repo_url": "FOO_REPO_URL",
        "baseline_sha": baseline_sha,
        "name": name,
        "client": client,
    }

    monkeypatch.setenv(DVC_STUDIO_URL, studio_url)
    monkeypatch.setenv(DVC_STUDIO_TOKEN, studio_token)
    monkeypatch.setenv(STUDIO_REPO_URL, repo_url)

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        event_type,
        baseline_sha,
        name,
        client,
    )

    mocked_post.assert_called_with(
        post_url,
        json=base_event,
        headers=headers,
        timeout=(30, 5),
    )

    assert post_live_metrics(
        event_type,
        baseline_sha,
        name,
        client,
        params={"params.yaml": {"foo": "bar"}},
    )

    mocked_post.assert_called_with(
        post_url,
        json={
            **base_event,
            "params": {"params.yaml": {"foo": "bar"}},
        },
        headers=headers,
        timeout=(30, 5),
    )

    subdir = "subdir"

    assert post_live_metrics(
        "start",
        baseline_sha,
        name,
        client,
        subdir=subdir,
    )

    mocked_post.assert_called_with(
        post_url,
        json={
            **base_event,
            "subdir": subdir,
        },
        headers=headers,
        timeout=(30, 5),
    )


def test_post_live_metrics_start_event_machine(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_URL, "https://0.0.0.0")
    monkeypatch.setenv(STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
        machine={"cpu": 1, "gpu": 2},
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0/api/live",
        json={
            "type": "start",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "machine": {"cpu": 1, "gpu": 2},
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=(30, 5),
    )


def test_post_live_metrics_data_skip_if_no_step(caplog, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    assert post_live_metrics("data", "f" * 40, "fooname", "fooclient") is None
    assert caplog.records[0].message == ("Missing `step` in `data` event.")


def copy_call_args(mock):
    new_mock = MagicMock()

    def side_effect(*args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        new_mock(*args, **kwargs)
        return DEFAULT

    mock.side_effect = side_effect
    return new_mock


def test_post_live_metrics_data(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    mocked_post = copy_call_args(mocked_post)

    assert post_live_metrics("data", "f" * 40, "fooname", "fooclient", step=0)
    mocked_post.assert_called_with(
        "https://studio.dvc.ai/api/live",
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
        timeout=(30, 5),
    )

    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        params={"dvclive/params.yaml": {"foo": "bar"}},
    )
    mocked_post.assert_called_with(
        "https://studio.dvc.ai/api/live",
        json={
            "type": "data",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "step": 0,
            "params": {"dvclive/params.yaml": {"foo": "bar"}},
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=(30, 5),
    )

    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    mocked_post = copy_call_args(mocked_post)

    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots={"dvclive/plots/metrics/foo.tsv": {"data": [{"step": 0, "foo": 1.0}]}},
    )

    mocked_post.assert_has_calls(
        [
            mocker.call(
                "https://studio.dvc.ai/api/live",
                json={
                    "type": "data",
                    "repo_url": "FOO_REPO_URL",
                    "baseline_sha": "f" * 40,
                    "name": "fooname",
                    "client": "fooclient",
                    "step": 0,
                    "metrics": {
                        "dvclive/metrics.json": {"data": {"step": 0, "foo": 1}},
                    },
                },
                headers={
                    "Authorization": "token FOO_TOKEN",
                    "Content-type": "application/json",
                },
                timeout=(30, 5),
            ),
            mocker.call(
                "https://studio.dvc.ai/api/live",
                json={
                    "type": "data",
                    "repo_url": "FOO_REPO_URL",
                    "baseline_sha": "f" * 40,
                    "name": "fooname",
                    "client": "fooclient",
                    "step": 0,
                    "plots": {
                        "dvclive/plots/metrics/foo.tsv": {
                            "data": [{"step": 0, "foo": 1.0}],
                        },
                    },
                },
                headers={
                    "Authorization": "token FOO_TOKEN",
                    "Content-type": "application/json",
                },
                timeout=(30, 5),
            ),
        ],
    )


def test_post_live_metrics_done(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

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
        "https://studio.dvc.ai/api/live",
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
        timeout=(30, 5),
    )

    assert post_live_metrics(
        "done",
        "f" * 40,
        "fooname",
        "fooclient",
        experiment_rev="h" * 40,
    )
    mocked_post.assert_called_with(
        "https://studio.dvc.ai/api/live",
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
        timeout=(30, 5),
    )

    assert post_live_metrics(
        "done",
        "f" * 40,
        "fooname",
        "fooclient",
        metrics={"dvclive/metris.json": {"data": {"foo": 1}}},
    )
    mocked_post.assert_called_with(
        "https://studio.dvc.ai/api/live",
        json={
            "type": "done",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "metrics": {"dvclive/metris.json": {"data": {"foo": 1}}},
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=(30, 5),
    )


def test_post_live_metrics_bad_response(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
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


def test_post_live_metrics_token_and_repo_url_args(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_URL, "https://0.0.0.0")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
        studio_token="FOO_TOKEN",
        studio_repo_url="FOO_REPO_URL",
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0/api/live",
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
        timeout=(30, 5),
    )


def test_post_live_metrics_message(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_URL, "https://0.0.0.0")
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)

    assert post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
        message="FOO_MESSAGE",
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0/api/live",
        json={
            "type": "start",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "message": "FOO_MESSAGE",
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=(30, 5),
    )

    # Test message length limit
    assert post_live_metrics(
        "start",
        "f" * 40,
        "fooname",
        "fooclient",
        message="X" * 100,
    )

    mocked_post.assert_called_with(
        "https://0.0.0.0/api/live",
        json={
            "type": "start",
            "repo_url": "FOO_REPO_URL",
            "baseline_sha": "f" * 40,
            "name": "fooname",
            "client": "fooclient",
            "message": "X" * 72,
        },
        headers={
            "Authorization": "token FOO_TOKEN",
            "Content-type": "application/json",
        },
        timeout=(30, 5),
    )


@pytest.mark.parametrize("var", [DVC_STUDIO_TOKEN, STUDIO_TOKEN])
def test_studio_token_envvar(monkeypatch, var):
    monkeypatch.setenv(var, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    assert get_studio_token_and_repo_url() == ("FOO_TOKEN", "FOO_REPO_URL")


def test_get_studio_token_and_repo_url_skip_repo_url(monkeypatch):
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    token, repo_url = get_studio_token_and_repo_url()
    assert token is None
    assert repo_url is None  # Skipped call to get_repo_url


def test_post_in_chunks(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200

    mocked_image = "foo" * 3000000

    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    mocked_post = copy_call_args(mocked_post)
    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots={"dvclive/plots/images/foo.png": {"image": mocked_image}},
    )
    # 1 call for metrics and params, 1 call for plots
    assert mocked_post.call_count == 2

    # 3.png will not be sent because it exceeds the limit size.
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    mocked_post = copy_call_args(mocked_post)
    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots={
            "dvclive/plots/images/0.png": {"image": mocked_image},
            "dvclive/plots/images/1.png": {"image": mocked_image},
            "dvclive/plots/images/2.png": {"image": mocked_image},
            "dvclive/plots/images/3.png": {"image": mocked_image},
        },
    )
    assert mocked_post.call_count == 2
    mocked_post.assert_has_calls(
        [
            mocker.call(
                "https://studio.dvc.ai/api/live",
                json={
                    "type": "data",
                    "repo_url": "FOO_REPO_URL",
                    "baseline_sha": "f" * 40,
                    "name": "fooname",
                    "client": "fooclient",
                    "step": 0,
                    "metrics": {
                        "dvclive/metrics.json": {"data": {"step": 0, "foo": 1}},
                    },
                },
                headers={
                    "Authorization": "token FOO_TOKEN",
                    "Content-type": "application/json",
                },
                timeout=(30, 5),
            ),
            mocker.call(
                "https://studio.dvc.ai/api/live",
                json={
                    "type": "data",
                    "repo_url": "FOO_REPO_URL",
                    "baseline_sha": "f" * 40,
                    "name": "fooname",
                    "client": "fooclient",
                    "step": 0,
                    "plots": {
                        "dvclive/plots/images/0.png": {"image": mocked_image},
                        "dvclive/plots/images/1.png": {"image": mocked_image},
                        "dvclive/plots/images/2.png": {"image": mocked_image},
                    },
                },
                headers={
                    "Authorization": "token FOO_TOKEN",
                    "Content-type": "application/json",
                },
                timeout=(30, 5),
            ),
        ],
    )


def test_post_in_chunks_skip_large_single_plot(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200

    mocked_image = mocker.MagicMock("foo")
    mocked_image.__len__.return_value = 29200000

    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots={"dvclive/plots/images/foo.png": {"image": mocked_image}},
    )
    assert mocked_post.call_count == 1


def test_post_in_chunks_max_number_of_plots(mocker, monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200

    plots = {}
    for i in range(MAX_NUMBER_OF_PLOTS + 2):
        plots[f"dvclive/plots/images/{i}.png"] = {
            "data": [{"step": i, "foo": float(i)}],
        }
    mocked_post = mocker.patch("requests.post", return_value=mocked_response)
    assert post_live_metrics(
        "data",
        "f" * 40,
        "fooname",
        "fooclient",
        step=0,
        metrics={"dvclive/metrics.json": {"data": {"step": 0, "foo": 1}}},
        plots=plots,
    )
    assert mocked_post.call_count == 2
    assert (
        len(mocked_post.call_args_list[-1][1]["json"]["plots"]) == MAX_NUMBER_OF_PLOTS
    )
