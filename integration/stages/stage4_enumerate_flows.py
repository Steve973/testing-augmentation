#!/usr/bin/env python3
"""
Stage 4: Enumerate Flows

Input: Integration graph from Stage 3
Output: All complete flows from entry points to terminal nodes

This stage performs graph traversal to find all complete flows:
- Start at each entry point
- Follow edges using depth-first search
- Stop at terminal nodes
- Detect and handle cycles

DEFAULT BEHAVIOR (no args):
  - Reads from ./integration-output/stage3-integration-graph.yaml
  - Outputs to ./integration-output/stage4-flows.yaml
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


def enumerate_flows(graph_data: dict[str, Any], verbose: bool = False) -> list[dict[str, Any]]:
    """
    Enumerate all complete flows through the integration graph.

    Uses depth-first search from each entry point, following edges
    until reaching terminal nodes. Detects cycles to prevent infinite loops.

    Args:
        graph_data: Integration graph from Stage 3
        verbose: Print progress information

    Returns:
        List of Flow dicts
    """
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    classification = graph_data.get('classification', {})

    entry_points = set(classification.get('entryPoints', []))
    terminal_nodes = set(classification.get('terminalNodes', []))

    if not nodes or not entry_points:
        return []

    # Build adjacency list for fast edge lookup
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        from_id = edge.get('from')
        to_id = edge.get('to')
        if from_id and to_id:
            if from_id not in adjacency:
                adjacency[from_id] = []
            adjacency[from_id].append(to_id)

    # Build node lookup
    nodes_by_id = {node['id']: node for node in nodes}

    flows = []
    flow_counter = 0
    max_depth = config.get_max_flow_depth()
    depth_warnings = 0
    max_warnings_to_show = 5
    max_flows_total = 10000  # Hard limit on total flows
    max_flows_per_entry = 100  # Limit flows from any single entry point

    if verbose:
        print(f"  Starting flow enumeration from {len(entry_points)} entry points...")
        print(f"  Max depth: {max_depth}")
        print(f"  Max flows per entry: {max_flows_per_entry}")
        print(f"  Max total flows: {max_flows_total}")

    # DFS from each entry point
    for entry_idx, entry_id in enumerate(entry_points):
        if entry_id not in nodes_by_id:
            continue

        if verbose and entry_idx % 10 == 0:
            print(f"  Processing entry point {entry_idx + 1}/{len(entry_points)}, found {flow_counter} flows so far...")

        if flow_counter >= max_flows_total:
            if verbose:
                print(f"  Reached max total flows ({max_flows_total}), stopping enumeration")
            break

        flows_from_this_entry = 0
        paths_explored_this_entry = 0
        max_paths_per_entry = 10000  # Stop exploring after this many path attempts

        # Stack: (current_id, path_so_far, visited_set)
        stack = [(entry_id, [entry_id], {entry_id})]

        while stack:
            current_id, path, visited = stack.pop()

            paths_explored_this_entry += 1

            # Check exploration limit
            if paths_explored_this_entry >= max_paths_per_entry:
                if verbose:
                    print(
                        f"    Entry {entry_id}: explored {paths_explored_this_entry} paths, found {flows_from_this_entry} flows, moving to next entry")
                break

            # Check flow limits
            if flows_from_this_entry >= max_flows_per_entry:
                # Stop exploring from this entry point
                break

            if flow_counter >= max_flows_total:
                break

            # Check if we've reached a terminal node
            if current_id in terminal_nodes:
                # Found a complete flow!
                flow_counter += 1
                flows_from_this_entry += 1
                flow_id = f"FLOW_{flow_counter:04d}"

                # Build flow sequence with full node data
                sequence = []
                for node_id in path:
                    if node_id in nodes_by_id:
                        sequence.append(nodes_by_id[node_id])

                # Determine entry point info
                entry_node = nodes_by_id.get(entry_id, {})
                entry_point_info = {
                    'integrationId': entry_id,
                    'unitId': entry_node.get('sourceUnit', 'unknown'),
                    'callableId': entry_node.get('sourceCallableId', 'unknown'),
                    'callableName': entry_node.get('sourceCallableName', 'unknown'),
                    'wayIn': f"Call {entry_node.get('sourceCallableName', 'unknown')} to reach first integration point"
                }

                # Determine terminal node info
                terminal_node = nodes_by_id.get(current_id, {})
                terminal_node_info = {
                    'integrationId': current_id,
                    'boundary': terminal_node.get('boundary', {}).get('kind') if terminal_node.get('boundary') else None
                }

                # Build flow description
                flow_description = ' → '.join([
                    nodes_by_id.get(node_id, {}).get('target', 'unknown')
                    for node_id in path
                ])

                flows.append({
                    'flowId': flow_id,
                    'description': flow_description,
                    'length': len(path),
                    'sequence': sequence,
                    'entryPoint': entry_point_info,
                    'terminalNode': terminal_node_info
                })

                continue  # Don't explore further from terminal nodes

            # Check depth limit
            if len(path) >= max_depth:
                depth_warnings += 1
                if verbose and depth_warnings <= max_warnings_to_show:
                    print(
                        f"    WARNING: Flow from {entry_id} reached max depth ({max_depth}), current path length: {len(path)}")
                    print(f"             Last few nodes: {' → '.join(path[-5:])}")
                continue

            # Explore neighbors
            neighbors = adjacency.get(current_id, [])
            for neighbor_id in neighbors:
                # Cycle detection: don't revisit nodes in current path
                if neighbor_id not in visited:
                    new_visited = visited.copy()
                    new_visited.add(neighbor_id)
                    stack.append((neighbor_id, path + [neighbor_id], new_visited))

    if verbose:
        print(f"  Found {len(flows)} complete flows")
        if depth_warnings > 0:
            print(f"  WARNING: {depth_warnings} paths hit max depth limit ({max_depth})")
            print(f"           This may indicate cycles or very deep chains")
            print(f"           Consider increasing max_flow_depth in config if needed")

    return flows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument(
        '--input',
        type=Path,
        default=config.get_stage_output(3),
        help=f'Integration graph from Stage 3 (default: {config.get_stage_output(3)})'
    )
    ap.add_argument(
        '--output',
        type=Path,
        default=config.get_stage_output(4),
        help=f'Output file (default: {config.get_stage_output(4)})'
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
        print(f"ERROR: Integration graph not found: {args.input}", file=sys.stderr)
        print("Run Stage 3 first.", file=sys.stderr)
        return 1

    # Load graph
    if args.verbose:
        print(f"Loading integration graph from: {args.input}")

    graph_data = yaml_load(args.input)

    node_count = len(graph_data.get('nodes', []))
    edge_count = len(graph_data.get('edges', []))

    if args.verbose:
        print(f"Loaded graph: {node_count} nodes, {edge_count} edges")

    # Enumerate flows
    if args.verbose:
        print("\nEnumerating flows...")

    flows = enumerate_flows(graph_data, verbose=args.verbose)

    # Build output
    output_data = {
        'stage': 'flow-enumeration',
        'flows': flows
    }

    if config.include_metadata():
        # Calculate stats
        total_length = sum(f['length'] for f in flows)
        avg_length = total_length / len(flows) if flows else 0
        max_length = max((f['length'] for f in flows), default=0)
        min_length = min((f['length'] for f in flows), default=0)

        output_data['metadata'] = {
            'flowCount': len(flows),
            'averageLength': round(avg_length, 2),
            'minLength': min_length,
            'maxLength': max_length,
            'totalIntegrationPoints': sum(f['length'] for f in flows)
        }

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    args.output.write_text(yaml_dump(output_data), encoding='utf-8')

    # Summary
    print(f"\n✓ Flow enumeration complete → {args.output}")
    print(f"  Total flows: {len(flows)}")

    if flows:
        lengths = [f['length'] for f in flows]
        print(f"  Flow lengths: {min(lengths)} - {max(lengths)} (avg: {sum(lengths) / len(lengths):.1f})")

    if not flows:
        print("\n  NOTE: No complete flows found.")
        print("  This means no paths exist from entry points to terminal nodes.")

    return 0


if __name__ == '__main__':
    sys.exit(main())