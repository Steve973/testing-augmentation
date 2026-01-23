#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from ruamel.yaml import YAML

"""
This module provides functions for loading YAML and JSON files, formatting validation errors,
and iterating over sorted validation errors.

Be sure that you have the required dependencies installed:
- jsonschema
- ruamel.yaml

``pip install jsonschema ruamel.yaml``

Usage:
    python unit-ledger-validator.py <unit-ledger.yaml> <schema.json>
"""


def load_multi_doc_yaml(path: Path) -> list[Any]:
    yaml = YAML(typ="safe")  # safe loader (no arbitrary Python objects)
    with path.open("r", encoding="utf-8") as f:
        docs = list(yaml.load_all(f))
    # ruamel returns None for empty docs; filter them out defensively
    return [d for d in docs if d is not None]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_path(error: ValidationError) -> str:
    # jsonschema gives a deque path; convert to a readable JSON Pointer-ish path
    parts = []
    for p in list(error.absolute_path):
        if isinstance(p, int):
            parts.append(f"[{p}]")
        else:
            parts.append(f".{p}" if parts else str(p))
    return "".join(parts) if parts else "<root>"


def iter_errors_sorted(
    validator: Draft202012Validator, instance: Any
) -> Iterable[ValidationError]:
    # Sort errors by location for more stable output
    errors = list(validator.iter_errors(instance))
    errors.sort(key=lambda e: (list(e.absolute_path), e.message))
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: unit_ledger_validator.py <unit-ledger.yaml> <schema.json>",
            file=sys.stderr,
        )
        return 2

    ledger_path = Path(argv[1])
    schema_path = Path(argv[2])

    ledger_docs = load_multi_doc_yaml(ledger_path)
    schema = load_json(schema_path)

    validator = Draft202012Validator(schema)

    errors = list(iter_errors_sorted(validator, ledger_docs))
    if not errors:
        print(f"OK: {ledger_path} validates against {schema_path}")
        return 0

    print(
        f"INVALID: {ledger_path} does not validate against {schema_path}",
        file=sys.stderr,
    )
    for i, err in enumerate(errors, start=1):
        loc = format_path(err)
        print(f"\n[{i}] at {loc}", file=sys.stderr)
        print(f"  message: {err.message}", file=sys.stderr)
        if err.schema_path:
            schema_loc = "/".join(str(x) for x in err.schema_path)
            print(f"  schema:  {schema_loc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
