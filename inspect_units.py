#!/usr/bin/env python3
"""
Extract all types (classes and functions) from a Python project.

Usage:
    python extract_project_types.py <project_root> [--output <file>]

Example:
    python extract_project_types.py ./src
    python extract_project_types.py ./src --output PROJECT_TYPES.txt
"""

import ast
import sys
from pathlib import Path
from typing import List, Set


def get_module_name_from_path(filepath: Path, project_root: Path) -> str:
    """
    Convert a file path to a module name.

    Example:
        /path/to/src/project/model/keys.py -> project.model.keys
    """
    relative = filepath.relative_to(project_root)
    parts = list(relative.parts[:-1]) + [relative.stem]

    # Remove __init__ from module name
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)


def extract_types_from_file(filepath: Path, project_root: Path) -> List[str]:
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

    module_name = get_module_name_from_path(filepath, project_root)
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


def extract_all_types(project_root: Path) -> Set[str]:
    """
    Extract all types from all Python files in the project.
    Returns a set of fully qualified type names.
    """
    all_types = set()

    if not project_root.exists():
        print(f"Error: Project root '{project_root}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not project_root.is_dir():
        print(f"Error: Project root '{project_root}' is not a directory", file=sys.stderr)
        sys.exit(1)

    python_files = list(project_root.rglob("*.py"))

    if not python_files:
        print(f"Warning: No Python files found in '{project_root}'", file=sys.stderr)

    print(f"Scanning {len(python_files)} Python files...", file=sys.stderr)

    for py_file in python_files:
        types = extract_types_from_file(py_file, project_root)
        all_types.update(types)

    return all_types


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print(__doc__)
        sys.exit(0)

    project_root = Path(sys.argv[1])
    output_file = None

    # Parse optional --output argument
    if len(sys.argv) >= 4 and sys.argv[2] == "--output":
        output_file = Path(sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[2] == "--output":
        print("Error: --output requires a filename", file=sys.stderr)
        sys.exit(1)

    # Extract types
    all_types = extract_all_types(project_root)

    # Sort for consistent output
    sorted_types = sorted(all_types)

    print(f"Found {len(sorted_types)} types", file=sys.stderr)

    # Output results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for type_name in sorted_types:
                f.write(f"{type_name}\n")
        print(f"Wrote types to {output_file}", file=sys.stderr)
    else:
        # Print to stdout
        for type_name in sorted_types:
            print(type_name)


if __name__ == "__main__":
    main()