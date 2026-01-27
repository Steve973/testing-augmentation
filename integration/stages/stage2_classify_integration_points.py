#!/usr/bin/env python3
"""
Stage 2: Classify Integration Points

Input: Integration points from Stage 1
Output: Classified integration points (entry/intermediate/terminal)

This stage classifies integration points based on their role in flows:
- Entry points: First seams (callables with no incoming interunit calls in scope)
- Terminal nodes: Boundaries OR callables with no outgoing interunit calls
- Intermediate: Everything else (has both incoming and outgoing)

DEFAULT BEHAVIOR (no args):
  - Reads from ./integration-output/stage1-integration-points.yaml
  - Outputs to ./integration-output/stage2-classified-points.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Add integration directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from shared.yaml_utils import yaml_load, yaml_dump


def classify_integration_points(points_data: dict[str, Any]) -> dict[str, Any]:
    """
    Classify integration points into entry/intermediate/terminal.

    Classification logic:
    - Entry point: Source callable has no incoming interunit calls
    - Terminal node: Boundary integration OR no outgoing interunit calls from target
    - Intermediate: Everything else

    Args:
        points_data: Integration points data from Stage 1

    Returns:
        Classification dict with categorized points
    """
    points = points_data.get('integrationPoints', [])

    if not points:
        return {
            'stage': 'integration-point-classification',
            'entryPoints': [],
            'intermediateSeams': [],
            'terminalNodes': [],
            'metadata': {
                'entryPointCount': 0,
                'intermediateCount': 0,
                'terminalNodeCount': 0,
                'totalPoints': 0
            }
        }

    # Build indexes for analysis
    # Map: callable_id -> list of integration point IDs where this callable is the SOURCE
    callables_with_outgoing = {}

    # Map: target_raw -> list of integration point IDs that call this target
    targets_with_incoming = {}

    # Set of all boundary integration IDs
    boundary_ids = set()

    for point in points:
        point_id = point.get('id')
        source_callable = point.get('sourceCallableId')
        target = point.get('target', '')

        # Track which callables have outgoing calls
        if source_callable:
            if source_callable not in callables_with_outgoing:
                callables_with_outgoing[source_callable] = []
            callables_with_outgoing[source_callable].append(point_id)

        # Track which targets have incoming calls
        if target:
            if target not in targets_with_incoming:
                targets_with_incoming[target] = []
            targets_with_incoming[target].append(point_id)

        # Track boundaries
        if point.get('boundary'):
            boundary_ids.add(point_id)

    # Now classify each point
    entry_points = []
    intermediate_seams = []
    terminal_nodes = []

    for point in points:
        point_id = point.get('id')
        source_callable = point.get('sourceCallableId')
        target = point.get('target', '')

        # Boundary integrations are ALWAYS terminal nodes
        if point_id in boundary_ids:
            terminal_nodes.append(point_id)
            continue

        # Check if source callable is an entry point (no incoming interunit calls)
        source_is_entry = source_callable not in targets_with_incoming

        # Check if target is a terminal (no outgoing calls)
        # We look for the target in our callables_with_outgoing map
        # If target is not there, it either:
        #   1. Is not in our scope (external/stdlib) -> treat as terminal
        #   2. Has no outgoing calls -> terminal
        target_is_terminal = target not in callables_with_outgoing

        # Classification decision tree:
        # - If source is entry AND target is terminal -> this is BOTH, but we'll call it entry
        # - If source is entry -> entry point
        # - If target is terminal -> terminal node
        # - Otherwise -> intermediate

        if source_is_entry:
            entry_points.append(point_id)
        elif target_is_terminal:
            terminal_nodes.append(point_id)
        else:
            intermediate_seams.append(point_id)

    # Build output
    result = {
        'stage': 'integration-point-classification',
        'entryPoints': entry_points,
        'intermediateSeams': intermediate_seams,
        'terminalNodes': terminal_nodes,
    }

    if config.include_metadata():
        result['metadata'] = {
            'entryPointCount': len(entry_points),
            'intermediateCount': len(intermediate_seams),
            'terminalNodeCount': len(terminal_nodes),
            'totalPoints': len(points),
            'boundaryCount': len(boundary_ids)
        }

    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument(
        '--input',
        type=Path,
        default=config.get_stage_input(2),
        help=f'Integration points file from Stage 1 (default: {config.get_stage_input(2)})'
    )
    ap.add_argument(
        '--output',
        type=Path,
        default=config.get_stage_output(2),
        help=f'Output file (default: {config.get_stage_output(2)})'
    )
    ap.add_argument(
        '--target-root',
        type=Path,
        help='Target project root (default: current directory)'
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

    # Validate input file exists
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        print("Run Stage 1 first to generate integration points.", file=sys.stderr)
        return 1

    # Load integration points
    if args.verbose:
        print(f"Loading integration points from: {args.input}")

    points_data = yaml_load(args.input)

    if args.verbose:
        total_points = len(points_data.get('integrationPoints', []))
        print(f"Loaded {total_points} integration points")

    # Classify
    if args.verbose:
        print("\nClassifying integration points...")

    classification = classify_integration_points(points_data)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    args.output.write_text(yaml_dump(classification), encoding='utf-8')

    # Summary
    entry_count = len(classification.get('entryPoints', []))
    intermediate_count = len(classification.get('intermediateSeams', []))
    terminal_count = len(classification.get('terminalNodes', []))

    print(f"\n✓ Classification complete → {args.output}")
    print(f"  Entry points: {entry_count}")
    print(f"  Intermediate: {intermediate_count}")
    print(f"  Terminal nodes: {terminal_count}")

    return 0


if __name__ == '__main__':
    sys.exit(main())