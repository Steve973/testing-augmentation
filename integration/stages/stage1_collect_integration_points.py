#!/usr/bin/env python3
"""
Stage 1: Collect Integration Points

Input: Collection of unit ledger files (auto-discovered or explicit)
Output: Flat list of all integration points with their contexts

This stage extracts all integration facts (interunit and boundary) from
unit ledgers and creates IntegrationPoint objects for each one.

DEFAULT BEHAVIOR (no args):
  - Discovers ledgers in ./ledgers
  - Outputs to ./integration-output/stage1-integration-points.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add integration directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config

from shared.data_structures import IntegrationPoint, TargetRef, BoundarySummary, IntegrationPointCollection
from shared.ledger_reader import discover_ledgers, load_ledgers, find_ledger_doc, extract_integration_facts
from shared.yaml_utils import yaml_dump


def create_integration_point(fact: dict) -> IntegrationPoint:
    """
    Create an IntegrationPoint object from an extracted integration fact.

    Args:
        fact: Integration fact dictionary from extract_integration_facts

    Returns:
        IntegrationPoint object
    """
    # Extract basic fields
    integration_id = fact.get('id', 'unknown')
    source_unit = fact.get('sourceUnit', 'unknown')
    source_callable_id = fact.get('sourceCallableId', 'unknown')
    source_callable_name = fact.get('sourceCallableName', 'unknown')
    target_raw = fact.get('target', '')
    kind = fact.get('kind', 'call')
    integration_type = fact.get('integrationType', 'unknown')

    # Extract execution paths
    execution_paths = fact.get('executionPaths', [])
    if not isinstance(execution_paths, list):
        execution_paths = []

    # Extract optional fields
    condition = fact.get('condition')
    signature = fact.get('signature')
    notes = fact.get('notes')

    # Create TargetRef (unresolved for now - Stage 2+ will resolve)
    target_resolved = TargetRef(
        status='unresolved',
        raw=target_raw
    )

    # Extract boundary information if this is a boundary integration
    boundary = None
    boundary_data = fact.get('boundary')
    if boundary_data and isinstance(boundary_data, dict):
        boundary = BoundarySummary(
            kind=boundary_data.get('kind', 'other'),
            protocol=boundary_data.get('protocol'),
            system=boundary_data.get('system'),
            endpoint=boundary_data.get('endpoint'),
            operation=boundary_data.get('operation'),
            resource=boundary_data.get('resource')
        )

    return IntegrationPoint(
        id=integration_id,
        integration_type=integration_type,
        source_unit=source_unit,
        source_callable_id=source_callable_id,
        source_callable_name=source_callable_name,
        target_raw=target_raw,
        target_resolved=target_resolved,
        kind=kind,
        execution_paths=execution_paths,
        condition=condition,
        boundary=boundary,
        signature=signature,
        notes=notes
    )


def collect_integration_points(ledger_paths: list[Path], verbose: bool = False) -> list[IntegrationPoint]:
    """
    Collect all integration points from the provided ledgers.

    Args:
        ledger_paths: Paths to unit ledger YAML files
        verbose: Print progress information

    Returns:
        List of IntegrationPoint objects
    """
    points = []

    # Load all ledgers
    ledgers = load_ledgers(ledger_paths)

    if verbose:
        print(f"Loaded {len(ledgers)} ledger(s)")

    # Extract integration facts from each ledger
    for ledger_data in ledgers:
        path = ledger_data['path']
        documents = ledger_data['documents']

        # Find the ledger document
        ledger_doc = find_ledger_doc(documents)
        if not ledger_doc:
            if verbose:
                print(f"  WARNING: No ledger document in {path.name}")
            continue

        unit_name = ledger_doc.get('unit', {}).get('name', 'unknown')

        # Extract integration facts
        facts = extract_integration_facts(ledger_doc)

        if verbose:
            print(f"  {path.name}: {len(facts)} integration point(s)")

        # Convert each fact to an IntegrationPoint object
        for fact in facts:
            try:
                point = create_integration_point(fact)
                points.append(point)
            except Exception as e:
                print(f"  WARNING: Failed to create integration point from {fact.get('id')}: {e}")

    return points


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument(
        'ledgers',
        nargs='*',
        type=Path,
        help='Unit ledger YAML files to process (default: auto-discover from --ledgers-root)'
    )
    ap.add_argument(
        '--ledgers-root',
        type=Path,
        default=config.get_ledgers_root(),
        help=f'Root directory for ledger discovery (default: {config.get_ledgers_root()})'
    )
    ap.add_argument(
        '--target-root',
        type=Path,
        help='Target project root (default: current directory)'
    )
    ap.add_argument(
        '--structure',
        choices=['auto', 'flat', 'package'],
        default=config.get_ledger_structure(),
        help=f'Ledger directory structure (default: {config.get_ledger_structure()})'
    )
    ap.add_argument(
        '--anchor',
        default=config.get_namespace_anchor(),
        help='Namespace anchor to strip for package resolution'
    )
    ap.add_argument(
        '--output',
        type=Path,
        default=config.get_stage_output(1),
        help=f'Output file (default: {config.get_stage_output(1)})'
    )
    ap.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = ap.parse_args(argv)

    # Set target root if provided
    if args.target_root:
        config.set_target_root(args.target_root)
        if args.verbose:
            print(f"Target root: {args.target_root}")

    # Determine ledger paths
    if args.ledgers:
        # Explicit ledgers provided
        ledger_paths = args.ledgers
        if args.verbose:
            print(f"Using {len(ledger_paths)} explicitly provided ledger(s)")
    else:
        # Auto-discover ledgers
        if args.verbose:
            print(f"Auto-discovering ledgers in: {args.ledgers_root}")

        ledger_paths = discover_ledgers(
            root=args.ledgers_root,
            structure=args.structure,
            anchor=args.anchor
        )

        if not ledger_paths:
            print(f"ERROR: No ledgers found in {args.ledgers_root}", file=sys.stderr)
            return 1

        if args.verbose:
            print(f"Discovered {len(ledger_paths)} ledger(s)")

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Collect integration points
    if args.verbose:
        print("\nCollecting integration points...")

    points = collect_integration_points(ledger_paths, verbose=args.verbose)

    if args.verbose:
        print(f"\nCollected {len(points)} total integration points")

        # Show breakdown
        interunit_count = sum(1 for p in points if p.integration_type == 'interunit')
        extlib_count = sum(1 for p in points if p.integration_type == 'extlib')
        stdlib_count = sum(1 for p in points if p.integration_type == 'stdlib')
        unknown_count = sum(1 for p in points if p.integration_type == 'unknown')
        boundary_count = sum(1 for p in points if p.boundary is not None)
        print(f"  Interunit: {interunit_count}")
        print(f"  Extlib: {extlib_count}")
        print(f"  Stdlib: {stdlib_count}")
        print(f"  Unknown: {unknown_count}")
        print(f"  Boundaries: {boundary_count}")

    # Build output collection
    collection = IntegrationPointCollection(
        points=points,
        ledger_count=len(ledger_paths) if config.include_metadata() else None,
        ledgers_root=str(args.ledgers_root) if config.include_metadata() and not args.ledgers else None,
        explicit_ledgers=[str(p) for p in args.ledgers] if config.include_metadata() and args.ledgers else None
    )

    # Write output
    args.output.write_text(yaml_dump(collection.to_dict()), encoding='utf-8')
    print(f"\n✓ Collected {len(points)} integration points → {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
