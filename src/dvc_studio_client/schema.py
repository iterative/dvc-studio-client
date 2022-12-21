from voluptuous import All, Any, Lower, Match, Required, Schema


def Choices(*choices):
    """Checks that value belongs to the specified set of values"""
    return Any(*choices, msg=f"expected one of {', '.join(choices)}")


Sha = All(Lower, Match(r"^[0-9a-h]{40}$"), msg="expected a length 40 commit sha")
# Supposed to be produced with:
#     {"cls": f"{e.__class__.__module__}.{e.__class__.__name__}", "text": str(e)}
ERROR_SCHEMA = {Required("cls"): str, Required("text"): str}

BASE_SCHEMA = Schema(
    {
        Required("type"): Choices("start", "done", "data"),  # No "interrupt" for now
        Required(
            "repo_url"
        ): str,  # TODO: use some url validator, voluptuous.Url is too strict
        Required("baseline_sha"): Sha,
        "name": str,
        "env": dict,
        "client": str,
        "errors": [ERROR_SCHEMA],
        "params": {str: dict},
        # Required("timestamp"): iso_datetime,  # TODO: decide if we need this
    }
)
SCHEMAS_BY_TYPE = {
    "start": BASE_SCHEMA,
    "data": BASE_SCHEMA.extend(
        {
            Required("step"): int,
            "metrics": {str: {"data": dict, "error": ERROR_SCHEMA}},
            "plots": {str: {"data": [dict], "props": dict, "error": ERROR_SCHEMA}},
        }
    ),
    "done": BASE_SCHEMA.extend(
        {
            "experiment_rev": Sha,
        }
    ),
}
