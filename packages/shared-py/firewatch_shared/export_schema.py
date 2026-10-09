"""Print one JSON Schema with every shared model under $defs.

Usage (from the repo root):
    uv run --package firewatch-shared python -m firewatch_shared.export_schema > packages/shared-ts/schema.json
"""

import json

from pydantic.json_schema import models_json_schema

from firewatch_shared.models import EXPORTED_MODELS


def build_schema() -> dict:
    _, schema = models_json_schema(
        [(model, "validation") for model in EXPORTED_MODELS],
        ref_template="#/$defs/{model}",
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema}


if __name__ == "__main__":
    print(json.dumps(build_schema(), indent=2, sort_keys=True))
