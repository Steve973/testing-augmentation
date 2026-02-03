#!/usr/bin/env python3
"""
Extract all types (classes and functions) from a Python project.

Generates project-inventory.txt for use in integration categorization.

Usage:
    python inspect_units.py <project_root> --source-root <src> --output-root <o>

Example:
    python inspect_units.py . --source-root src --output-root dist/inspect
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Set


# Directories to exclude from scanning
EXCLUDED_DIRS = {
    '.venv',
    'venv',
    '__pycache__',
    '.git',
    '.idea',
    '.vscode',
    'node_modules',
    'build',
    'dist',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    'eggs',
    '.eggs',
}


def should_skip_path(path: Path) -> bool:
    """Check if a path should be skipped during scanning."""
    # Skip if any parent directory is in excluded list
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
    return False


def get_module_name_from_path(filepath: Path, source_root: Path) -> str:
    """
    Convert a file path to a module name.

    Example:
        /path/to/src/project/model/keys.py -> project.model.keys
    """
    relative = filepath.relative_to(source_root)
    parts = list(relative.parts[:-1]) + [relative.stem]

    # Remove __init__ from module name
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)


def extract_types_from_file(filepath: Path, source_root: Path) -> List[str]:
    """
    Extract all class and function definitions from a Python file.
    Returns fully qualified names.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
        return []

    module_name = get_module_name_from_path(filepath, source_root)
    types = []

    def visit_node(node, parent_name=None):
        """Recursively visit AST nodes to find classes and functions."""
        current_name = parent_name

        if isinstance(node, ast.ClassDef):
            qualified_name = f"{module_name}.{node.name}" if not parent_name else f"{parent_name}.{node.name}"
            types.append(qualified_name)
            current_name = qualified_name

            # Visit nested classes and methods
            for child in node.body:
                visit_node(child, current_name)

        elif isinstance(node, ast.FunctionDef):
            if parent_name:
                # Method inside a class
                qualified_name = f"{parent_name}.{node.name}"
            else:
                # Top-level function
                qualified_name = f"{module_name}.{node.name}"
            types.append(qualified_name)

        elif isinstance(node, ast.AsyncFunctionDef):
            if parent_name:
                qualified_name = f"{parent_name}.{node.name}"
            else:
                qualified_name = f"{module_name}.{node.name}"
            types.append(qualified_name)

    # Visit all top-level nodes
    for node in tree.body:
        visit_node(node)

    return types


def extract_all_types(source_root: Path) -> Set[str]:
    """
    Extract all types from all Python files in the source root.
    Returns a set of fully qualified type names.
    """
    all_types = set()

    if not source_root.exists():
        print(f"Error: Source root '{source_root}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not source_root.is_dir():
        print(f"Error: Source root '{source_root}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all Python files, filtering out excluded directories
    python_files = [
        f for f in source_root.rglob("*.py")
        if not should_skip_path(f) and f.name != "__init__.py"
    ]

    if not python_files:
        print(f"Warning: No Python files found in '{source_root}'", file=sys.stderr)
        return all_types

    print(f"Scanning {len(python_files)} Python files...")

    for py_file in python_files:
        types = extract_types_from_file(py_file, source_root)
        all_types.update(types)

    return all_types


def main():
    parser = argparse.ArgumentParser(
        description="Extract all types from a Python project for integration categorization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  %(prog)s /path/to/project --source-root src --output-root dist/inspect
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
        default='dist/inspect',
        help='Output root relative to project root (default: "dist/inspect")'
    )

    args = parser.parse_args()

    project_root = args.project_root.absolute()
    source_root = project_root / args.source_root

    if not source_root.exists():
        print(f"Error: Source root not found: {source_root}", file=sys.stderr)
        sys.exit(1)

    # Extract types
    all_types = extract_all_types(source_root)

    # Sort for consistent output
    sorted_types = sorted(all_types)

    print(f"Found {len(sorted_types)} types")

    # Output to project-inventory.txt in output-root
    output_root = project_root / args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    output_file = output_root / "project-inventory.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        for type_name in sorted_types:
            f.write(f"{type_name}\n")

    print(f"Wrote project inventory to {output_file}")


if __name__ == "__main__":
    main()