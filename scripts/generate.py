"""Regenerates the types in src/zerogen/types from openapi.json.

Run it with `uv run scripts/generate.py`. With `--fetch`, it first downloads the
published OpenAPI document (or ZEROGEN_OPENAPI_URL) into openapi.json.

Request bodies become TypedDicts with the API's own field names. Responses become
pydantic models with snake_case fields. Response models drop the document's
constraints and accept enum values and fields they don't know yet, so a client
keeps working when the API adds one.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "openapi.json"
TYPES = ROOT / "src" / "zerogen" / "types"
DEFAULT_URL = "https://api.zerogen.com/v1/openapi.json"
REQUESTS = ("CreateGenerationRequest", "CreateUploadRequest")
HEADER = "# Generated from openapi.json by scripts/generate.py. Don't edit it by hand."
CONSTRAINTS = {
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "propertyNames",
}
COMMON = [
    "--input-file-type=openapi",
    "--target-python-version=3.10",
    "--use-standard-collections",
    "--use-union-operator",
    "--enum-field-as-literal=all",
    "--naming-strategy=parent-prefixed",
    "--use-field-description",
    "--use-double-quotes",
    "--disable-timestamp",
    "--formatters=ruff-format",
    f"--custom-file-header={HEADER}",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate src/zerogen/types from openapi.json.")
    parser.add_argument(
        "--fetch", action="store_true", help="download the published document first"
    )
    if parser.parse_args().fetch:
        fetch()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schemas: dict[str, Any] = spec["components"]["schemas"]
    requests = {name: schemas[name] for name in REQUESTS}
    responses = {name: loosen(schema) for name, schema in schemas.items() if name not in REQUESTS}
    with tempfile.TemporaryDirectory() as scratch:
        generate(
            document(spec, requests, Path(scratch, "requests.json")),
            TYPES / "_requests.py",
            ["--output-model-type=typing.TypedDict"],
        )
        generate(
            document(spec, responses, Path(scratch, "responses.json")),
            TYPES / "_responses.py",
            [
                "--output-model-type=pydantic_v2.BaseModel",
                "--base-class=zerogen._models.BaseModel",
                "--snake-case-field",
                "--output-datetime-class=datetime",
            ],
        )
    write_index()


def fetch() -> None:
    url = os.environ.get("ZEROGEN_OPENAPI_URL", DEFAULT_URL)
    with urllib.request.urlopen(url) as response:
        spec = json.load(response)
    SPEC.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote openapi.json from {url}")


def loosen(schema: Any) -> Any:
    """Drops a response schema's constraints, and lets each enum take any string too."""
    if not isinstance(schema, dict):
        return schema
    items = cast("dict[str, Any]", schema).items()
    out: dict[str, Any] = {key: value for key, value in items if key not in CONSTRAINTS}
    if out.get("additionalProperties") is False:
        del out["additionalProperties"]
    if "properties" in out:
        out["properties"] = {name: loosen(value) for name, value in out["properties"].items()}
    for key in ("items", "additionalProperties"):
        if isinstance(out.get(key), dict):
            out[key] = loosen(out[key])
    for key in ("anyOf", "oneOf", "allOf"):
        if key in out:
            out[key] = [loosen(value) for value in out[key]]
    if "enum" in out or "const" in out:
        values = out.pop("enum") if "enum" in out else [out.pop("const")]
        description = out.pop("description", None)
        out = {"anyOf": [{**out, "enum": values}, {"type": out.get("type", "string")}]}
        if description is not None:
            out["description"] = description
    return out


def document(spec: dict[str, Any], schemas: dict[str, Any], path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "openapi": spec["openapi"],
                "info": spec["info"],
                "paths": {},
                "components": {"schemas": schemas},
            }
        ),
        encoding="utf-8",
    )
    return path


def generate(source: Path, output: Path, options: list[str]) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            f"--input={source}",
            f"--output={output}",
            *COMMON,
            *options,
        ],
        check=True,
        cwd=ROOT,
    )
    output.write_bytes(output.read_bytes().replace(b"\r\n", b"\n"))
    print(f"Wrote {output.relative_to(ROOT).as_posix()}")


def write_index() -> None:
    lines = [HEADER, ""]
    names: list[str] = []
    for module in ("_requests", "_responses"):
        tree = ast.parse((TYPES / f"{module}.py").read_text(encoding="utf-8"))
        classes = sorted(node.name for node in tree.body if isinstance(node, ast.ClassDef))
        lines += [f"from .{module} import (", *(f"    {name}," for name in classes), ")"]
        names += classes
    lines += ["", "__all__ = [", *(f'    "{name}",' for name in sorted(names)), "]", ""]
    (TYPES / "__init__.py").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("Wrote src/zerogen/types/__init__.py")


if __name__ == "__main__":
    main()
