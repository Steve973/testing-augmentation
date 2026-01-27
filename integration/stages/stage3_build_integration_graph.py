#!/usr/bin/env python3
"""
Stage 3: Build Integration Graph

Input: Classified integration points from Stage 2 + original points from Stage 1
Output: Integration graph with edges between integration points

This stage constructs edges between integration points using the rule:
  Edge exists from I1 to I2 if I1.target matches I2.source_callable

The graph shows which integration points can lead to other integration points,
forming the basis for flow enumeration in Stage 4.

DEFAULT BEHAVIOR (no args):
  - Reads Stage 1 and Stage 2 outputs
  - Outputs to ./integration-output/stage3-integration-graph.yaml
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


def build_integration_graph(
        points_data: dict[str, Any],
        classification_data: dict[str, Any],
        verbose: bool = False
) -> dict[str, Any]:
    """
    Build graph with edges between integration points.

    Edge determination rule:
      Edge from I1 to I2 exists if:
        I1.target callable matches I2.source_callable

    This means: "If integration I1 happens (calls target), does that put us
    inside the callable that contains I2?"

    Args:
        points_data: Integration points from Stage 1
        classification_data: Classification from Stage 2
        verbose: Print progress information

    Returns:
        Graph dict with nodes and edges
    """
    points = points_data.get('integrationPoints', [])

    if not points:
        return {
            'stage': 'integration-graph',
            'nodes': [],
            'edges': [],
            'metadata': {
                'nodeCount': 0,
                'edgeCount': 0
            }
        }

    # Build lookup: integration_id -> full integration point data
    points_by_id = {p['id']: p for p in points}

    # Build lookup: source_callable_id -> list of integration IDs that originate from it
    integrations_by_source_callable = {}
    for point in points:
        source_callable = point.get('sourceCallableId')
        if source_callable:
            if source_callable not in integrations_by_source_callable:
                integrations_by_source_callable[source_callable] = []
            integrations_by_source_callable[source_callable].append(point['id'])

    # Build edges
    edges = []

    for point in points:
        point_id = point['id']
        target = point.get('target', '')

        if not target:
            continue

        # Check if this target matches any source callable
        # The target might be:
        #   - A simple name: "some_function"
        #   - A qualified name: "SomeClass.method"
        #   - A fully qualified name: "module.SomeClass.method"

        # Strategy: Check if target string appears as a callable ID
        # or if any callable's name matches the target

        # First, try exact match on callable ID (unlikely but possible)
        if target in integrations_by_source_callable:
            # Direct match - target IS a callable ID
            for target_integration_id in integrations_by_source_callable[target]:
                edges.append({
                    'from': point_id,
                    'to': target_integration_id,
                    'reason': f'{point_id} calls {target}, which contains {target_integration_id}'
                })

        # Second, try matching target against callable names
        # Look for integrations whose source callable NAME matches the target
        for other_point in points:
            other_id = other_point['id']
            other_source_callable = other_point.get('sourceCallableId')
            other_source_name = other_point.get('sourceCallableName', '')

            # Skip self
            if other_id == point_id:
                continue

            # Check if target matches the callable name
            # Handle various matching scenarios:
            #   - Exact match: target == "method_name"
            #   - Class.method match: target == "ClassName.method_name"
            #   - Qualified match: target ends with callable name

            if target == other_source_name:
                # Exact name match
                edges.append({
                    'from': point_id,
                    'to': other_id,
                    'reason': f'{point_id} calls {target}, which contains {other_id}'
                })
            elif '.' in target and target.endswith('.' + other_source_name):
                # Qualified name match (e.g., "SomeClass.method" matches "method")
                edges.append({
                    'from': point_id,
                    'to': other_id,
                    'reason': f'{point_id} calls {target}, which contains {other_id}'
                })
            elif target.endswith(other_source_name):
                # Partial match (be conservative here)
                # Only match if it looks like ClassName.methodName or module.ClassName.methodName
                if '.' in target:
                    edges.append({
                        'from': point_id,
                        'to': other_id,
                        'reason': f'{point_id} calls {target}, which contains {other_id}'
                    })

    if verbose:
        print(f"  Built {len(edges)} edges between {len(points)} nodes")

    # Build output
    result = {
        'stage': 'integration-graph',
        'nodes': points,  # Include full point data
        'edges': edges,
        'classification': {
            'entryPoints': classification_data.get('entryPoints', []),
            'intermediateSeams': classification_data.get('intermediateSeams', []),
            'terminalNodes': classification_data.get('terminalNodes', [])
        }
    }

    if config.include_metadata():
        result['metadata'] = {
            'nodeCount': len(points),
            'edgeCount': len(edges),
            'entryPointCount': len(classification_data.get('entryPoints', [])),
            'intermediateCount': len(classification_data.get('intermediateSeams', [])),
            'terminalNodeCount': len(classification_data.get('terminalNodes', []))
        }

    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument(
        '--points',
        type=Path,
        default=config.get_stage_output(1),  # Stage 1 has the full point data
        help=f'Integration points from Stage 1 (default: {config.get_stage_output(1)})'
    )
    ap.add_argument(
        '--classification',
        type=Path,
        default=config.get_stage_output(2),  # Stage 2 has the classification
        help=f'Classification from Stage 2 (default: {config.get_stage_output(2)})'
    )
    ap.add_argument(
        '--output',
        type=Path,
        default=config.get_stage_output(3),
        help=f'Output file (default: {config.get_stage_output(3)})'
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

    # Validate input files exist
    if not args.points.exists():
        print(f"ERROR: Integration points file not found: {args.points}", file=sys.stderr)
        print("Run Stage 1 first.", file=sys.stderr)
        return 1

    if not args.classification.exists():
        print(f"ERROR: Classification file not found: {args.classification}", file=sys.stderr)
        print("Run Stage 2 first.", file=sys.stderr)
        return 1

    # Load data
    if args.verbose:
        print(f"Loading integration points from: {args.points}")
    points_data = yaml_load(args.points)

    if args.verbose:
        print(f"Loading classification from: {args.classification}")
    classification_data = yaml_load(args.classification)

    total_points = len(points_data.get('integrationPoints', []))
    if args.verbose:
        print(f"Loaded {total_points} integration points")

    # Build graph
    if args.verbose:
        print("\nBuilding integration graph...")

    graph = build_integration_graph(points_data, classification_data, verbose=args.verbose)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    args.output.write_text(yaml_dump(graph), encoding='utf-8')

    # Summary
    node_count = len(graph.get('nodes', []))
    edge_count = len(graph.get('edges', []))

    print(f"\n✓ Graph construction complete → {args.output}")
    print(f"  Nodes: {node_count}")
    print(f"  Edges: {edge_count}")

    if edge_count == 0:
        print("\n  NOTE: No edges found. This means no integration points lead to others.")
        print("  This could indicate:")
        print("    - All integration points are to external/stdlib code")
        print("    - Integration points don't chain (each is independent)")
        print("    - Target names don't match source callable names (naming mismatch)")

    return 0


if __name__ == '__main__':
    sys.exit(main())