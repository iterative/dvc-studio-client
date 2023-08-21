import os

import pytest
from dulwich.porcelain import clone, init

from dvc_studio_client import DEFAULT_STUDIO_URL
from dvc_studio_client.config import _get_remote_url, get_studio_config
from dvc_studio_client.env import (
    DVC_STUDIO_OFFLINE,
    DVC_STUDIO_REPO_URL,
    DVC_STUDIO_TOKEN,
    DVC_STUDIO_URL,
    STUDIO_REPO_URL,
    STUDIO_TOKEN,
)


def test_get_url(monkeypatch, tmp_path_factory):
    source = os.fspath(tmp_path_factory.mktemp("source"))
    target = os.fspath(tmp_path_factory.mktemp("target"))
    with init(source), clone(source, target):
        monkeypatch.chdir(target)
        assert _get_remote_url() == source


@pytest.mark.parametrize(
    "token,repo_url",
    [(DVC_STUDIO_TOKEN, DVC_STUDIO_REPO_URL), (STUDIO_TOKEN, STUDIO_REPO_URL)],
)
def test_studio_config_envvar(monkeypatch, token, repo_url):
    monkeypatch.setenv(token, "FOO_TOKEN")
    monkeypatch.setenv(repo_url, "FOO_REPO_URL")
    assert get_studio_config() == {
        "token": "FOO_TOKEN",
        "repo_url": "FOO_REPO_URL",
        "url": DEFAULT_STUDIO_URL,
    }


def test_studio_config_dvc_studio_config():
    dvc_studio_config = {
        "token": "FOO_TOKEN",
        "repo_url": "FOO_REPO_URL",
        "url": "FOO_URL",
    }
    expected = {
        "token": "FOO_TOKEN",
        "repo_url": "FOO_REPO_URL",
        "url": "FOO_URL",
    }
    assert get_studio_config(dvc_studio_config=dvc_studio_config) == expected


def test_studio_config_kwarg():
    expected = {
        "token": "FOO_TOKEN",
        "repo_url": "FOO_REPO_URL",
        "url": "FOO_URL",
    }
    assert (
        get_studio_config(
            studio_token="FOO_TOKEN",
            studio_repo_url="FOO_REPO_URL",
            studio_url="FOO_URL",
        )
        == expected
    )


def test_studio_config_envvar_override(monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(DVC_STUDIO_URL, "FOO_URL")
    monkeypatch.setenv(DVC_STUDIO_REPO_URL, "FOO_REPO_URL")
    dvc_studio_config = {
        "token": "BAR_TOKEN",
        "url": "BAR_URL",
    }
    expected = {
        "token": "FOO_TOKEN",
        "repo_url": "FOO_REPO_URL",
        "url": "FOO_URL",
    }
    assert get_studio_config(dvc_studio_config=dvc_studio_config) == expected


def test_studio_config_kwarg_override(monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(DVC_STUDIO_REPO_URL, "FOO_REPO_URL")
    monkeypatch.setenv(DVC_STUDIO_URL, "FOO_URL")
    expected = {
        "token": "BAR_TOKEN",
        "repo_url": "BAR_REPO_URL",
        "url": "BAR_URL",
    }
    assert (
        get_studio_config(
            studio_token="BAR_TOKEN",
            studio_repo_url="BAR_REPO_URL",
            studio_url="BAR_URL",
        )
        == expected
    )


@pytest.mark.parametrize(
    "val",
    ("1", "y", "yes", "true", True, 1),
)
def test_studio_config_offline(monkeypatch, val):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(DVC_STUDIO_REPO_URL, "FOO_REPO_URL")

    assert get_studio_config() != {}

    assert get_studio_config(offline=val) == {}

    monkeypatch.setenv(DVC_STUDIO_OFFLINE, val)
    assert get_studio_config() == {}

    monkeypatch.setenv(DVC_STUDIO_OFFLINE, val)
    assert get_studio_config() == {}

    assert get_studio_config(dvc_studio_config={"offline": True}) == {}


def test_studio_config_infer_url(monkeypatch):
    monkeypatch.setenv(DVC_STUDIO_TOKEN, "FOO_TOKEN")
    monkeypatch.setenv(DVC_STUDIO_REPO_URL, "FOO_REPO_URL")

    assert get_studio_config()["url"] == DEFAULT_STUDIO_URL


def test_get_studio_config_skip_repo_url(monkeypatch):
    monkeypatch.setenv(STUDIO_REPO_URL, "FOO_REPO_URL")
    config = get_studio_config()
    assert config == {}  # Skipped call to get_repo_url
