#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

_ENTRY_ID_RE = re.compile(r"\bC[0-9]{3}(?:(?:N|F|M)[0-9]{3}|[A-Z][0-9]{3})*\b")


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def _safe_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _read_multi_doc_yaml(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    return [d for d in docs if d is not None]


def _find_doc(docs: list[Any], doc_kind: str) -> dict[str, Any] | None:
    for d in docs:
        dd = _safe_dict(d)
        if dd.get("docKind") == doc_kind:
            return dd
    return None


def _walk_yaml_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".yml", ".yaml"}:
            out.append(p)
    out.sort(key=lambda p: str(p).lower())
    return out


def _entry_children(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in _safe_list(entry.get("children")) if isinstance(c, dict)]


def _iter_entries_depth_first(entry: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [entry]
    for c in _entry_children(entry):
        out.extend(_iter_entries_depth_first(c))
    return out


def _extract_type_name(type_ref: Any) -> str | None:
    tr = _safe_dict(type_ref)
    name = tr.get("name")
    return name if isinstance(name, str) and name else None


def _normalize_target(
        raw: Any,
        index: dict[str, Any],
        *,
        from_unit_id: str | None = None,
        from_unit_name: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw_s = raw.strip()

    by_entry_id = _safe_dict(index.get("byEntryId"))
    by_address = _safe_dict(index.get("byAddress"))
    by_name = _safe_dict(index.get("byName"))
    by_qualified = _safe_dict(index.get("byQualified"))
    by_local_path = _safe_dict(index.get("byLocalPath"))

    def _resolved(cand: dict[str, Any]) -> dict[str, Any]:
        c = _safe_dict(cand)
        return {
            "status": "resolved",
            "raw": raw_s,
            "unitId": c.get("unitId"),
            "entryId": c.get("entryId"),
            "name": c.get("name"),
            "address": c.get("address"),
        }

    def _ambiguous(note: str, candidates: list[Any]) -> dict[str, Any]:
        return {"status": "ambiguous", "raw": raw_s, "note": note, "candidates": candidates}

    def _unresolved(note: str) -> dict[str, Any]:
        return {"status": "unresolved", "raw": raw_s, "note": note}

    # 1) explicit entry id in text
    m = _ENTRY_ID_RE.search(raw_s)
    if m:
        eid = m.group(0)
        candidates = _safe_list(by_entry_id.get(eid))
        if len(candidates) == 1:
            return _resolved(_safe_dict(candidates[0]))
        if len(candidates) > 1 and from_unit_id:
            same = [c for c in candidates if _safe_dict(c).get("unitId") == from_unit_id]
            if len(same) == 1:
                return _resolved(_safe_dict(same[0]))
        if len(candidates) > 1:
            return _ambiguous(f"EntryId {eid} matched multiple records", candidates)
        return _unresolved(f"EntryId {eid} not present in index")

    # 2) exact address
    addr_candidates = _safe_list(by_address.get(raw_s))
    if len(addr_candidates) == 1:
        return _resolved(_safe_dict(addr_candidates[0]))
    if len(addr_candidates) > 1:
        return _ambiguous("address matched multiple records", addr_candidates)

    # 3) qualified match (best for your `project_resolution_engine.internal.resolvelib....`)
    qual_candidates = _safe_list(by_qualified.get(raw_s))
    if len(qual_candidates) == 1:
        return _resolved(_safe_dict(qual_candidates[0]))
    if len(qual_candidates) > 1 and from_unit_id:
        same = [c for c in qual_candidates if _safe_dict(c).get("unitId") == from_unit_id]
        if len(same) == 1:
            return _resolved(_safe_dict(same[0]))
    if len(qual_candidates) > 1:
        return _ambiguous("qualified name matched multiple records", qual_candidates)

    # 4) if it's in *this* unit namespace, try local path after stripping unit prefix
    if isinstance(from_unit_name, str) and from_unit_name and raw_s.startswith(from_unit_name + "."):
        local = raw_s[len(from_unit_name) + 1:]
        local_candidates = _safe_list(by_local_path.get(local))
        if len(local_candidates) == 1:
            return _resolved(_safe_dict(local_candidates[0]))
        if len(local_candidates) > 1 and from_unit_id:
            same = [c for c in local_candidates if _safe_dict(c).get("unitId") == from_unit_id]
            if len(same) == 1:
                return _resolved(_safe_dict(same[0]))
        if len(local_candidates) > 1:
            return _ambiguous("local path matched multiple records", local_candidates)

    # 5) safe name-only match: ONLY when raw is not dotted
    if "." not in raw_s and "::" not in raw_s:
        name_candidates = _safe_list(by_name.get(raw_s))
        if len(name_candidates) == 1:
            return _resolved(_safe_dict(name_candidates[0]))
        if len(name_candidates) > 1 and from_unit_id:
            same = [c for c in name_candidates if _safe_dict(c).get("unitId") == from_unit_id]
            if len(same) == 1:
                return _resolved(_safe_dict(same[0]))
        if len(name_candidates) > 1:
            return _ambiguous("name matched multiple records", name_candidates)

    return _unresolved("no deterministic match (no EntryId/address/qualified/local-path hit)")


def _extract_callable_summary(entry: dict[str, Any]) -> dict[str, Any] | None:
    if entry.get("kind") != "callable":
        return None

    callable_spec = _safe_dict(entry.get("callable"))
    if not callable_spec:
        return None

    params: list[dict[str, Any]] = []
    for p in _safe_list(callable_spec.get("params")):
        pd = _safe_dict(p)
        if not pd:
            continue
        params.append(
            {
                "name": pd.get("name"),
                "type": _extract_type_name(pd.get("type")),
                "default": pd.get("default", None) if "default" in pd else None,
                "notes": pd.get("notes"),
            }
        )

    branches: list[dict[str, Any]] = []
    for b in _safe_list(callable_spec.get("branches")):
        bd = _safe_dict(b)
        if not bd:
            continue
        branches.append(
            {
                "id": bd.get("id"),
                "precondition": bd.get("precondition"),
                "condition": bd.get("condition"),
                "outcome": bd.get("outcome"),
                "notes": bd.get("notes"),
            }
        )

    integration = _safe_dict(callable_spec.get("integration"))
    interunit: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []

    if integration:
        for f in _safe_list(integration.get("interunit")):
            fd = _safe_dict(f)
            if not fd:
                continue
            interunit.append(
                {
                    "target": fd.get("target"),
                    "kind": fd.get("kind"),
                    "via": fd.get("via"),
                    "signature": fd.get("signature"),
                    "condition": fd.get("condition"),
                    "notes": fd.get("notes"),
                    # targetRef added later (second pass) once global index exists
                }
            )

        for f in _safe_list(integration.get("boundaries")):
            fd = _safe_dict(f)
            if not fd:
                continue
            bsum = _safe_dict(fd.get("boundary"))
            boundaries.append(
                {
                    "target": fd.get("target"),
                    "kind": fd.get("kind"),
                    "via": fd.get("via"),
                    "condition": fd.get("condition"),
                    "boundary": {
                        "kind": bsum.get("kind"),
                        "system": bsum.get("system"),
                        "operation": bsum.get("operation"),
                        "endpoint": bsum.get("endpoint"),
                        "resource": bsum.get("resource"),
                        "protocol": bsum.get("protocol"),
                        "notes": bsum.get("notes"),
                    }
                    if bsum
                    else None,
                    "notes": fd.get("notes"),
                }
            )

    throws: list[str] = []
    for t in _safe_list(callable_spec.get("throws")):
        tn = _extract_type_name(t)
        if tn:
            throws.append(tn)

    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "signature": entry.get("signature"),
        "visibility": entry.get("visibility"),
        "modifiers": _safe_list(entry.get("modifiers")),
        "params": params,
        "returnType": _extract_type_name(callable_spec.get("returnType")),
        "throws": throws,
        "branches": branches,
        "integration": {
            "interunit": interunit,
            "boundaries": boundaries,
            "notes": integration.get("notes") if integration else None,
        },
        "notes": entry.get("notes"),
    }


def _dedupe_index_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for r in records:
        key = (
            str(r.get("unitId") or ""),
            str(r.get("entryId") or ""),
            str(r.get("name") or ""),
            str(r.get("fqName") or ""),
            str(r.get("address") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _iter_entry_index_records(
        derived: dict[str, Any] | None, ledger_unit: dict[str, Any], unit_id: str | None, unit_name: str | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    if derived:
        assigned = _safe_dict(derived.get("assigned"))
        for e in _safe_list(assigned.get("entries")):
            ed = _safe_dict(e)
            if not ed:
                continue
            out.append(
                {
                    "unitId": unit_id,
                    "unitName": unit_name,
                    "entryId": ed.get("id"),
                    "name": ed.get("name"),
                    "address": ed.get("address"),
                }
            )

    # Only fallback when derived ids didn't give us anything
    if not out:
        for e in _iter_entries_depth_first(ledger_unit):
            ed = _safe_dict(e)
            if not ed:
                continue
            eid = ed.get("id")
            nm = ed.get("name")
            if not eid or not nm:
                continue
            out.append(
                {
                    "unitId": unit_id,
                    "unitName": unit_name,
                    "entryId": eid,
                    "name": nm,
                    "address": ed.get("address"),
                }
            )

    out.sort(
        key=lambda r: (
            str(r.get("unitId") or ""),
            str(r.get("entryId") or ""),
            str(r.get("name") or ""),
            str(r.get("address") or ""),
        )
    )
    return out


def _address_local_path(addr: Any) -> str | None:
    # expected-ish: "C000::ProjectResolutionProvider.find_matches@L123"
    if not isinstance(addr, str) or "::" not in addr:
        return None
    rest = addr.split("::", 1)[1]
    local = rest.split("@", 1)[0]
    return local.strip() or None


def _build_global_entry_index(unit_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_entry_id: dict[str, list[dict[str, Any]]] = {}
    by_address: dict[str, list[dict[str, Any]]] = {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    by_qualified: dict[str, list[dict[str, Any]]] = {}
    by_local_path: dict[str, list[dict[str, Any]]] = {}

    for r in unit_records:
        eid = r.get("entryId")
        addr = r.get("address")
        nm = r.get("name")
        unit_name = r.get("unitName")

        if isinstance(eid, str) and eid:
            by_entry_id.setdefault(eid, []).append(r)
        if isinstance(addr, str) and addr:
            by_address.setdefault(addr, []).append(r)
        if isinstance(nm, str) and nm:
            by_name.setdefault(nm, []).append(r)

        local = _address_local_path(addr)
        if isinstance(local, str) and local:
            by_local_path.setdefault(local, []).append(r)
            if isinstance(unit_name, str) and unit_name:
                by_qualified.setdefault(f"{unit_name}.{local}", []).append(r)

    return {
        "byEntryId": by_entry_id,
        "byAddress": by_address,
        "byName": by_name,
        "byQualified": by_qualified,
        "byLocalPath": by_local_path,
    }


def _copy_candidate_records(candidates: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in _safe_list(candidates):
        if isinstance(c, dict):
            out.append(dict(c))
    return out


def _yaml_dump(data: Any) -> str:
    return yaml.dump(
        data,
        Dumper=_NoAliasDumper,
        sort_keys=False,
        default_flow_style=False,
        indent=2,
        width=100,
        allow_unicode=True,
        explicit_start=False,
        explicit_end=False,
    )


def _prune(x: Any) -> Any:
    if isinstance(x, dict):
        out: dict[str, Any] = {}
        for k, v in x.items():
            pv = _prune(v)
            if pv is None:
                continue
            if pv == "":
                continue
            if isinstance(pv, (list, dict)) and not pv:
                continue
            out[k] = pv
        return out
    if isinstance(x, list):
        out_list = []
        for v in x:
            pv = _prune(v)
            if pv is None:
                continue
            if pv == "":
                continue
            if isinstance(pv, (list, dict)) and not pv:
                continue
            out_list.append(pv)
        return out_list
    return x


def _to_yaml(consolidated: dict[str, Any], source_root: str | None = None) -> str:
    units: list[dict[str, Any]] = consolidated.get("units", []) or []
    edges: list[dict[str, Any]] = consolidated.get("edges", []) or []
    meta: dict[str, Any] = {
        "unitCount": len(units),
        "interunitEdgeCount": len(edges),
    }
    if source_root:
        meta["sourceRoot"] = source_root

    # keep any supplemental meta-counts if present
    idx = _safe_dict(consolidated.get("index"))
    if idx:
        meta["index"] = idx

    doc: dict[str, Any] = {
        "kind": "ledger-consolidation",
        "meta": meta,
        "edges": edges,
        "units": units,
    }
    doc = _prune(doc)
    return _yaml_dump(doc)


def extract(root: Path) -> dict[str, Any]:
    units_out: list[dict[str, Any]] = []
    edges_out: list[dict[str, Any]] = []
    index_records: list[dict[str, Any]] = []

    parsed: list[dict[str, Any]] = []

    # pass 1: parse + collect index records
    for path in _walk_yaml_files(root):
        try:
            docs = _read_multi_doc_yaml(path)
        except Exception as e:
            units_out.append(
                {"source": str(path), "error": f"failed to parse YAML: {e}"}
            )
            continue

        derived = _find_doc(docs, "derived-ids")
        ledger = _find_doc(docs, "ledger")
        if not ledger:
            continue

        ledger_unit = _safe_dict(ledger.get("unit"))

        unit_name = None
        unit_lang = None
        unit_id = None

        if derived:
            unit = _safe_dict(derived.get("unit"))
            unit_name = unit.get("name")
            unit_lang = unit.get("language")
            unit_id = unit.get("unitId")

        if not unit_name:
            unit_name = ledger_unit.get("name")
        if not unit_id:
            unit_id = ledger_unit.get("id")
        if not unit_lang:
            unit_lang = None

        index_records.extend(_iter_entry_index_records(derived, ledger_unit, unit_id, unit_name))

        parsed.append(
            {
                "source": str(path),
                "ledger_unit": ledger_unit,
                "unitId": unit_id,
                "unitName": unit_name,
                "unitLang": unit_lang,
            }
        )

    index_records = _dedupe_index_records(index_records)
    global_index = _build_global_entry_index(index_records)

    # pass 2: extract callables + edges, now with normalization
    for rec in parsed:
        unit_id = rec.get("unitId")
        unit_name = rec.get("unitName")
        unit_lang = rec.get("unitLang")
        source = rec.get("source")
        ledger_unit = _safe_dict(rec.get("ledger_unit"))

        callables_out: list[dict[str, Any]] = []

        for e in _iter_entries_depth_first(ledger_unit):
            ed = _safe_dict(e)
            cs = _extract_callable_summary(ed)
            if not cs:
                continue

            integ = _safe_dict(cs.get("integration"))
            interunit = _safe_list(integ.get("interunit"))

            # normalize inline facts
            for f in interunit:
                if not isinstance(f, dict):
                    continue

                raw_target = f.get("target")
                if not raw_target:
                    continue

                f["targetRef"] = _normalize_target(
                    raw_target,
                    global_index,
                    from_unit_id=unit_id,
                    from_unit_name=unit_name,
                )

            callables_out.append(cs)

            # build edges (edge-level from + pure to targetRef)
            for f in interunit:
                if not isinstance(f, dict):
                    continue
                raw_target = f.get("target")
                if not raw_target:
                    continue

                edges_out.append(
                    {
                        "from": {"unitId": unit_id, "callableId": cs.get("id")},
                        "to": _normalize_target(
                            raw_target,
                            global_index,
                            from_unit_id=unit_id,
                            from_unit_name=unit_name),
                        "kind": f.get("kind"),
                        "via": f.get("via"),
                        "condition": f.get("condition"),
                        "source": source,
                    }
                )

        units_out.append(
            {
                "unitId": unit_id,
                "name": unit_name,
                "language": unit_lang,
                "source": source,
                "callables": callables_out,
            }
        )

    edges_out = sorted(
        edges_out,
        key=lambda e: (
            str(_safe_dict(e.get("from")).get("unitId") or ""),
            str(_safe_dict(e.get("from")).get("callableId") or ""),
            str(_safe_dict(e.get("to")).get("raw") or ""),
            str(e.get("kind") or ""),
        ),
    )

    return {
        "units": units_out,
        "edges": edges_out,
        "index": {
            "recordCount": len(index_records),
            "byEntryIdCount": len(_safe_dict(global_index.get("byEntryId"))),
            "byAddressCount": len(_safe_dict(global_index.get("byAddress"))),
            "byNameCount": len(_safe_dict(global_index.get("byName"))),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract flow-friendly summaries from unit ledger YAML files."
    )
    ap.add_argument(
        "root",
        type=str,
        help="Ledger file or directory containing ledgers (*.yml/*.yaml).",
    )
    ap.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml).",
    )
    ap.add_argument(
        "--out",
        type=str,
        default="-",
        help="Output path, or '-' for stdout (default: '-').",
    )
    args = ap.parse_args()

    consolidated = extract(Path(args.root))

    if args.format == "json":
        out_text = json.dumps(consolidated, indent=2, sort_keys=False) + "\n"
    else:
        out_text = _to_yaml(consolidated, source_root=str(Path(args.root)))

    if args.out == "-":
        print(out_text, end="")
    else:
        Path(args.out).write_text(out_text, encoding="utf-8")


if __name__ == "__main__":
    main()
