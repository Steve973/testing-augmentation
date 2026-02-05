#!/usr/bin/env python3
"""
Project Analysis Coordinator

Orchestrates the multi-stage pipeline for analyzing Python projects:
1. inspect_units.py - Basic unit structure
2. enumerate_exec_items.py - EI enumeration
3. enumerate_callables.py - Integration classification + EI merging
4. inventory_to_ledger.py - Generate three-document ledgers
"""

import argparse
import subprocess
import sys
from pathlib import Path

from callable_id_generation import generate_unit_id


def run_command(cmd: list[str], description: str, log_dir: Path = Path("/tmp/ledger")) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 70}")
    print(f"{description}")
    print(f"{'=' * 70}")
    print(f"Command: {' '.join(str(c) for c in cmd)}\n")

    Path.mkdir(log_dir, exist_ok=True, parents=True)

    # Create log file name from description
    log_name = description.lower().replace(' ', '_').replace(':', '').replace('-', '_') + '.log'
    log_file = log_dir / log_name

    with open(log_file, 'w') as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)

    if result.returncode != 0:
        print(f"\n✗ Failed: {description}")
        print(f"   See log: {log_file}")
        return False

    print(f"\n✓ Completed: {description}")
    print(f"   Log: {log_file}")
    return True


def derive_fqn(filepath: Path, source_root: Path) -> str:
    """Derive fully qualified name from filepath."""
    try:
        relative = filepath.relative_to(source_root)
    except ValueError:
        # If the filepath is not relative to source_root, use absolute
        relative = filepath

    # Remove .py extension and convert path separators to dots
    fqn = str(relative.with_suffix('')).replace('/', '.').replace('\\', '.')

    # Remove __init__ if present
    if fqn.endswith('.__init__'):
        fqn = fqn[:-9]

    return fqn


def analyze_project(
        project_root: Path,
        source_root: str = "src",
        output_root: str = "dist",
) -> bool:
    """
    Run full analysis pipeline on a project.

    Pipeline stages:
    1. inspect_units - Generate basic unit structure
    2. enumerate_exec_items - Enumerate execution items (EIs)
    3. enumerate_callables - Classify integrations and merge EI data
    """

    project_root = project_root.absolute()
    source_path = project_root / source_root

    if not source_path.exists():
        print(f"Error: Source root not found: {source_path}")
        return False

    # Output directories
    inspect_output = project_root / output_root / "inspect"
    eis_output = project_root / output_root / "eis"
    inventory_output = project_root / output_root / "inventory"
    ledgers_output = project_root / output_root / "ledgers"

    print(f"\n{'=' * 70}")
    print(f"Project Analysis Pipeline")
    print(f"{'=' * 70}")
    print(f"Project root:      {project_root}")
    print(f"Source root:       {source_path}")
    print(f"Inspect output:    {inspect_output}")
    print(f"EIs output:        {eis_output}")
    print(f"Inventory output:  {inventory_output}")
    print(f"Ledgers output:    {ledgers_output}")
    print(f"{'=' * 70}")

    # Stage 1: inspect_units (if it exists)
    inspect_script = Path(__file__).parent / "inspect_units.py"
    if inspect_script.exists():
        cmd = [
            sys.executable,
            str(inspect_script),
            str(project_root),
            "--source-root", source_root,
            "--output-root", str(inspect_output.relative_to(project_root))
        ]
        if not run_command(cmd, "Stage 1: Inspect Units"):
            return False
    else:
        print(f"\nℹ  Skipping Stage 1: inspect_units.py not found")

    # Stage 2: enumerate_exec_items
    enumerate_eis_script = Path(__file__).parent / "enumerate_exec_items.py"
    if not enumerate_eis_script.exists():
        print(f"Error: enumerate_exec_items.py not found at {enumerate_eis_script}")
        return False

    # Create output directory
    eis_output.mkdir(parents=True, exist_ok=True)

    # Find all Python files
    py_files = list(source_path.rglob("*.py"))
    py_files = [f for f in py_files if f.name != "__init__.py"]

    print(f"\n{'=' * 70}")
    print(f"Stage 2: Enumerate Execution Items")
    print(f"{'=' * 70}")
    print(f"Found {len(py_files)} Python files\n")

    for py_file in sorted(py_files):
        rel_path = py_file.relative_to(source_path)
        output_file = eis_output / rel_path.parent / f"{py_file.stem}_eis.yaml"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(enumerate_eis_script),
            str(py_file),
            "--unit-id", generate_unit_id(derive_fqn(py_file, source_path)),
            "--output", str(output_file)
        ]

        print(f"Processing: {rel_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  ✗ Failed")
            print(result.stderr)
        else:
            print(f"  ✓ {output_file.relative_to(project_root)}")

    print(f"\n✓ Completed: Stage 2")

    # Stage 3: enumerate_callables (per-file processing)
    enumerate_callables_script = Path(__file__).parent / "enumerate_callables.py"
    if not enumerate_callables_script.exists():
        print(f"Error: enumerate_callables.py not found at {enumerate_callables_script}")
        return False

    # Create output directory
    inventory_output.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 70}")
    print(f"Stage 3: Enumerate Callables + Merge EI Data")
    print(f"{'=' * 70}")
    print(f"Processing {len(py_files)} Python files\n")

    for py_file in sorted(py_files):
        rel_path = py_file.relative_to(source_path)
        fqn = derive_fqn(py_file, source_path)
        if fqn.endswith('.__init__'):
            fqn = fqn[:-9]

        cmd = [
            sys.executable,
            str(enumerate_callables_script),
            "--file", str(py_file),
            "--fqn", fqn,
            "--unit-id", generate_unit_id(fqn),
            "--output-root", str(inventory_output),
            "--ei-root", str(eis_output)
        ]

        print(f"Processing: {rel_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  ✗ Failed")
            print(result.stderr)
        else:
            print(f"  ✓ Inventory generated")

        print(f"result: {result.stdout}")

    print(f"\n✓ Completed: Stage 3")

    # Stage 4: Generate ledgers
    inventory_to_ledger_script = Path(__file__).parent / "inventory_to_ledger.py"
    if not inventory_to_ledger_script.exists():
        print(f"\nℹ  Skipping Stage 4: inventory_to_ledger.py not found")
    else:
        # Create ledgers output directory
        ledgers_output.mkdir(parents=True, exist_ok=True)

        # Find all inventory files
        inventory_files = list(inventory_output.rglob("*.inventory.yaml"))

        print(f"\n{'=' * 70}")
        print(f"Stage 4: Generate Ledgers")
        print(f"{'=' * 70}")
        print(f"Found {len(inventory_files)} inventory files\n")

        # Check for project inventory
        project_inventory_file = inspect_output / "project-inventory.txt"
        if not project_inventory_file.exists():
            project_inventory_file = None
            print(f"Note: No project-inventory.txt found, integrations may be categorized as unknown\n")

        for inventory_file in sorted(inventory_files):
            rel_path = inventory_file.relative_to(inventory_output)
            ledger_file = ledgers_output / rel_path.parent / f"{inventory_file.stem.replace('.inventory', '')}.ledger.yaml"
            ledger_file.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                sys.executable,
                str(inventory_to_ledger_script),
                "--inventory", str(inventory_file),
                "--output", str(ledger_file)
            ]

            if project_inventory_file:
                cmd.extend(["--project-inventory", str(project_inventory_file)])

            print(f"Processing: {rel_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"  ✗ Failed")
                if result.stderr:
                    print(result.stderr)
            else:
                print(f"  ✓ {ledger_file.relative_to(project_root)}")

        print(f"\n✓ Completed: Stage 4")

    print(f"\n{'=' * 70}")
    print(f"✓ Analysis Complete!")
    print(f"{'=' * 70}")
    print(f"\nOutputs:")
    if inspect_output.exists():
        print(f"  - Unit inspection: {inspect_output} (YAML)")
    print(f"  - EI enumeration:  {eis_output} (YAML)")
    print(f"  - Final inventory: {inventory_output} (YAML)")
    if ledgers_output.exists():
        print(f"  - Unit ledgers:    {ledgers_output} (YAML)")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Coordinate multi-stage analysis pipeline for Python projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline Stages:
  1. inspect_units.py        - Generate basic unit structure (optional)
  2. enumerate_exec_items.py - Enumerate execution items (EIs)
  3. enumerate_callables.py  - Classify integrations + merge EI data
  4. inventory_to_ledger.py  - Generate three-document unit ledgers

Example:
  %(prog)s /path/to/project --source-root src --output-root dist
        """
    )

    parser.add_argument(
        'project_root',
        type=Path,
        help='Project root directory'
    )
    parser.add_argument(
        '--source-root',
        type=str,
        default='src',
        help='Source root relative to project root (default: "src")'
    )
    parser.add_argument(
        '--output-root',
        type=str,
        default='dist',
        help='Output root relative to project root (default: "dist")'
    )

    args = parser.parse_args()

    if not args.project_root.exists():
        print(f"Error: Project root not found: {args.project_root}")
        sys.exit(1)

    success = analyze_project(
        args.project_root,
        args.source_root,
        args.output_root
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()