"""Shape pydantic's JSON Schema into the form MCP clients read best.

Tool input models are pydantic ``BaseModel`` subclasses, and
``model_json_schema()`` already carries every constraint (``type: integer``,
``enum``, ``minimum`` / ``maximum``, ``default``, lengths, patterns). Two
pydantic habits make the advertised schema harder to read than the
TypeScript sibling's, so ``mcp_input_schema`` rewrites them:

* An optional field (``Optional[X] = None``) becomes
  ``{"anyOf": [X, {"type": "null"}], "default": null}``. Clients that look
  for ``enum`` or ``minimum`` directly on the property miss them, and some
  clients mishandle ``anyOf``. The field is optional because it is absent
  from ``required``, so the schema advertises ``X`` itself (no null branch,
  no ``default: null``). Validation still runs through pydantic, so an
  explicit ``null`` from a client is accepted exactly as before.
* Every model and property gets a generated ``title`` ("Entity Slug"),
  which repeats the name and is dropped.

The result matches what the TypeScript package advertises for the same zod
schema. Validation is unaffected: arguments are always checked by the
pydantic model, never by this advertised schema.
"""

from __future__ import annotations

import copy
from typing import Any


def _collapse_nullable(prop: dict[str, Any]) -> dict[str, Any]:
    any_of = prop.get("anyOf")
    if not isinstance(any_of, list):
        return prop
    branches = [b for b in any_of if not (isinstance(b, dict) and b.get("type") == "null")]
    if len(branches) != 1 or len(branches) == len(any_of):
        # Either a real union (several non-null branches) or no null branch
        # at all: leave it alone.
        return prop
    merged: dict[str, Any] = dict(branches[0])
    for key, value in prop.items():
        if key != "anyOf":
            merged[key] = value
    return merged


def _clean_property(prop: Any) -> Any:
    if not isinstance(prop, dict):
        return prop
    out = _collapse_nullable(prop)
    out.pop("title", None)
    if "default" in out and out["default"] is None:
        del out["default"]
    items = out.get("items")
    if isinstance(items, dict):
        out["items"] = _clean_property(items)
    return out


def mcp_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a cleaned copy of a pydantic model JSON Schema for tools/list."""
    out = copy.deepcopy(schema)
    out.pop("title", None)
    out.setdefault("type", "object")
    props = out.get("properties")
    if isinstance(props, dict):
        out["properties"] = {name: _clean_property(p) for name, p in props.items()}
    else:
        out["properties"] = {}
    return out
