import logging
from os import getenv
from typing import Any, Dict, Literal, Optional

import requests
from git import Repo
from git.exc import GitError
from requests.exceptions import RequestException
from voluptuous import Invalid, MultipleInvalid
from voluptuous.humanize import humanize_error

from .env import STUDIO_ENDPOINT, STUDIO_REPO_URL, STUDIO_TOKEN
from .schema import SCHEMAS_BY_TYPE

logger = logging.getLogger(__name__)
logger.setLevel(getenv("DVC_STUDIO_CLIENT_LOGLEVEL", "INFO").upper())

                          
def _get_remote_url(git_repo):
    return git_repo.git.ls_remote("--get-url")


def get_studio_repo_url() -> Optional[str]:
    studio_url = None
    try:
        git_repo = Repo()
        studio_url = _get_remote_url(git_repo)
    except GitError:
        logger.debug("Tried to find remote url for the active branch but failed.\n")
    finally:
        if not studio_url:
            logger.warning(
                "Couldn't find a valid Studio Repo URL.\n"
                "You can try manually setting the environment variable "
                f"`{STUDIO_REPO_URL}`."
            )
        return studio_url  # noqa: B012  # pylint:disable=lost-exception


def get_studio_token_and_repo_url():
    studio_token = getenv(STUDIO_TOKEN, None)
    if studio_token is None:
        logger.debug("STUDIO_TOKEN not found. Skipping `post_studio_live_metrics`")
        return None, None

    studio_repo_url = getenv(STUDIO_REPO_URL, None)
    if studio_repo_url is None:
        logger.debug(f"`{STUDIO_REPO_URL}` not found. Trying to automatically find it.")
        studio_repo_url = get_studio_repo_url()
    return studio_token, studio_repo_url


def post_live_metrics(
    event_type: Literal["start", "data", "done"],
    baseline_sha: str,
    name: str,
    client: Literal["dvc", "dvclive"],
    experiment_rev: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    plots: Optional[Dict[str, Any]] = None,
    step: Optional[int] = None,
) -> Optional[bool]:
    """Post `event_type` to Studio's `api/live`.

    Requires the environment variable `STUDIO_TOKEN` to be set.
    If the environment variable `STUDIO_REPO_URL` is not set, will attempt to
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
        step: (Optional[int]): Current step of the training loop.
            Usually comes from DVCLive `Live.step` property.
            Required in when `event_type="data"`.
            Defaults to `None`.

    Returns:
        Optional[bool]:
            `True` - if received status code 200 from Studio.
            `False` - if received other status code or RequestException raised.
            `None`- if prerequisites weren't met and the request was not sent.
    """
    studio_token, studio_repo_url = get_studio_token_and_repo_url()

    if any(x is None for x in (studio_token, studio_repo_url)):
        return None

    body = {
        "type": event_type,
        "repo_url": studio_repo_url,
        "baseline_sha": baseline_sha,
        "name": name,
        "client": client,
    }

    if params:
        body["params"] = params

    if event_type == "data":
        if step is None:
            logger.warning("Missing `step` in `data` event.")
            return None
        body["step"] = step
        if metrics:
            body["metrics"] = metrics
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
        logger.debug(humanize_error(body, e))
        return None

    logger.info(f"post_studio_live_metrics `{event_type=}`")
    logger.debug(f"JSON body `{body=}`")

    try:
        response = requests.post(
            getenv(STUDIO_ENDPOINT, "https://studio.iterative.ai/api/live"),
            json=body,
            headers={
                "Content-type": "application/json",
                "Authorization": f"token {studio_token}",
            },
            timeout=5,
        )
    except RequestException:
        return False

    message = response.content.decode()
    logger.debug(
        f"post_to_studio: {response.status_code=}" f", {message=}" if message else ""
    )

    return response.status_code == 200
