#!/usr/bin/env python3
"""
Execution Item Enumerator - Complete Python Statement Coverage

Enumerates all execution items (EIs) in Python source code.
Outputs YAML format for integration with pipeline.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Any, Callable

import yaml

from callable_id_generation import generate_function_id, generate_ei_id
from models import Branch


# ============================================================================
# Operation Extraction
# ============================================================================

def extract_all_operations(node: ast.AST) -> list[ast.Call]:
    """
    Extract ALL Call nodes from an AST in execution order.

    For nested/chained calls like Path(fetch(url)).resolve():
    - Returns: [fetch(url), Path(...), Path(...).resolve()]
    - Execution order: innermost first (by depth), then left-to-right

    Returns:
        List of ast.Call nodes in execution order
    """
    operations = []

    # Collect all Call nodes with their depth
    def collect_calls_with_depth(n: ast.AST, depth: int = 0) -> None:
        """Recursively collect calls with their nesting depth."""
        if isinstance(n, ast.Call):
            # Record this call with its depth and position
            operations.append((n, depth, n.lineno, n.col_offset))

        # Recurse into children with increased depth
        for child in ast.iter_child_nodes(n):
            collect_calls_with_depth(child, depth + 1)

    collect_calls_with_depth(node)

    # Sort by: depth (deepest/innermost first), then line, then column
    # This gives us execution order: inner calls before outer calls
    operations.sort(key=lambda x: (-x[1], x[2], x[3]))

    # Return just the Call nodes
    return [op[0] for op in operations]


# ============================================================================
# Statement Decomposers
# ============================================================================

def decompose_if(stmt: ast.If, source_lines: list[str]) -> list[str]:
    """If statement: 2 EIs (true/false)."""
    condition = ast.unparse(stmt.test)

    # Check what's inside the if body for better descriptions
    if stmt.body:
        first_stmt = stmt.body[0]

        # If it raises, be specific
        if isinstance(first_stmt, ast.Raise):
            exc = ast.unparse(first_stmt.exc) if first_stmt.exc else "exception"
            return [
                f"{condition} is true → raises {exc}",
                f"{condition} is false → continues"
            ]

        # If it returns, be specific
        if isinstance(first_stmt, ast.Return):
            ret_val = ast.unparse(first_stmt.value) if first_stmt.value else "None"
            return [
                f"{condition} is true → returns {ret_val}",
                f"{condition} is false → continues"
            ]

    # Generic if
    return [
        f"{condition} is true → enters if block",
        f"{condition} is false → continues"
    ]


def decompose_for(stmt: ast.For, source_lines: list[str]) -> list[str]:
    """
    For loop: 2 EIs (0 iterations, ≥1 iterations).
    For-else: 3 EIs (empty, completes without break, breaks).
    """
    target = ast.unparse(stmt.target)
    iter_expr = ast.unparse(stmt.iter)

    if stmt.orelse:
        # For-else pattern
        return [
            f"for {target} in {iter_expr}: 0 iterations → else executes",
            f"for {target} in {iter_expr}: completes without break → else executes",
            f"for {target} in {iter_expr}: breaks → else skipped"
        ]
    else:
        # Regular for loop
        return [
            f"for {target} in {iter_expr}: 0 iterations",
            f"for {target} in {iter_expr}: ≥1 iterations"
        ]


def decompose_while(stmt: ast.While, source_lines: list[str]) -> list[str]:
    """
    While loop: 2 EIs (initially false, initially true).
    While-else: 3 EIs (initially false → else, completes → else, breaks → no else).
    """
    condition = ast.unparse(stmt.test)

    if stmt.orelse:
        # While-else pattern
        return [
            f"while {condition}: initially false → else executes",
            f"while {condition}: completes without break → else executes",
            f"while {condition}: breaks → else skipped"
        ]
    else:
        # Regular while loop
        return [
            f"while {condition}: initially false → 0 iterations",
            f"while {condition}: initially true → ≥1 iterations"
        ]


def decompose_try(stmt: ast.Try, source_lines: list[str]) -> list[str]:
    """
    Try/except: 1 + N EIs (success + each handler).
    Try/except/else: adds 1 EI for else block.
    Finally always executes, doesn't create separate EI for branching.
    """
    outcomes = ["try block executes successfully"]

    # Add EI for each exception handler
    for handler in stmt.handlers:
        if handler.type:
            exc_type = ast.unparse(handler.type)
            outcomes.append(f"raises {exc_type} → enters except handler")
        else:
            outcomes.append(f"raises exception → enters except handler")

    # Note: else block executes only if try succeeds (already covered by first EI)
    # Note: finally block always executes (not a branching point)

    return outcomes


def decompose_with(stmt: ast.With, source_lines: list[str]) -> list[str]:
    """With statement: 2 EIs (enters successfully, raises on entry)."""
    contexts = [ast.unparse(item.context_expr) for item in stmt.items]
    context_str = ', '.join(contexts)
    return [
        f"with {context_str}: enters successfully",
        f"with {context_str}: raises exception on entry"
    ]


def decompose_match(stmt: ast.Match, source_lines: list[str]) -> list[str]:
    """Match statement: N EIs (one per case)."""
    outcomes = []
    for i, case in enumerate(stmt.cases):
        pattern = ast.unparse(case.pattern)

        # Check if case body contains a return statement
        has_return = any(isinstance(node, ast.Return) for node in case.body)

        if has_return:
            outcomes.append(f"match case {i + 1}: {pattern} → returns")
        else:
            outcomes.append(f"match case {i + 1}: {pattern}")
    return outcomes


def decompose_assert(stmt: ast.Assert, source_lines: list[str]) -> list[str]:
    """Assert statement: 2 EIs (assertion holds, assertion fails)."""
    test = ast.unparse(stmt.test)
    return [
        f"assert {test}: holds → continues",
        f"assert {test}: fails → raises AssertionError"
    ]


def decompose_assignment(stmt: ast.Assign, source_lines: list[str]) -> list[str]:
    """
    Assignment: Enumerate all operations, then the assignment itself.
    Special cases:
    - List/dict/set comprehension: 2-3 EIs
    - Ternary expression: 4 EIs
    - Operations (calls, chained/nested): separate EIs for each
    """
    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)

    # List comprehension
    if isinstance(stmt.value, ast.ListComp):
        return decompose_comprehension(stmt.value, "list", "[]")

    # Dict comprehension
    if isinstance(stmt.value, ast.DictComp):
        return decompose_comprehension(stmt.value, "dict", "{}")

    # Set comprehension
    if isinstance(stmt.value, ast.SetComp):
        return decompose_comprehension(stmt.value, "set", "set()")

    # Ternary expression (IfExp)
    if isinstance(stmt.value, ast.IfExp):
        return decompose_ternary(stmt.value)

    # Extract all operations (calls, in execution order)
    operations = extract_all_operations(stmt.value)

    if operations:
        eis = []
        for op_call in operations:
            call_str = ast.unparse(op_call)
            eis.append(f"{call_str} succeeds")
            eis.append(f"{call_str} raises exception → exception propagates")

        # Only add "all operations succeed" EI if there are multiple operations
        if len(operations) > 1:
            eis.append(f"all operations succeed → {line_text}")

        return eis

    # Regular assignment (no operations)
    return [f"executes: {line_text}"]


def decompose_comprehension(comp: ast.ListComp | ast.DictComp | ast.SetComp, comp_type: str, empty_repr: str) -> list[
    str]:
    """Comprehension: 3 EIs with filter, 2 without."""
    has_filter = any(gen.ifs for gen in comp.generators)

    if has_filter:
        return [
            f"{comp_type} comprehension: source empty → {empty_repr}",
            f"{comp_type} comprehension: source has items, all filtered → {empty_repr}",
            f"{comp_type} comprehension: source has items, some pass filter → populated"
        ]
    else:
        return [
            f"{comp_type} comprehension: source empty → {empty_repr}",
            f"{comp_type} comprehension: source has items → populated"
        ]


def contains_call_that_can_raise(node: ast.AST) -> tuple[bool, str | None]:
    """
    Check if an AST node contains function calls that can raise exceptions.

    Returns:
        (has_calls, call_description) - call_description is the unparsed call if found
    """
    # Walk the AST to find Call nodes
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            call_str = ast.unparse(child)
            # Most function calls can potentially raise exceptions
            # (We could be more selective here, but for now assume all can raise)
            return True, call_str
    return False, None


def decompose_ternary(ifexp: ast.IfExp) -> list[str]:
    """Ternary expression: 4 EIs (condition branches + value assignments)."""
    condition = ast.unparse(ifexp.test)
    true_val = ast.unparse(ifexp.body)
    false_val = ast.unparse(ifexp.orelse)
    return [
        f"{condition} is true → continues to true branch",
        f"{condition} is false → continues to false branch",
        f"true branch: assigns {true_val}",
        f"false branch: assigns {false_val}"
    ]


def decompose_augassign(stmt: ast.AugAssign, source_lines: list[str]) -> list[str]:
    """Augmented assignment (+=, -=, etc.): 1 EI."""
    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)
    return [f"executes: {line_text}"]


def decompose_annassign(stmt: ast.AnnAssign, source_lines: list[str]) -> list[str]:
    """Annotated assignment: 1 EI."""
    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)
    return [f"executes: {line_text}"]


def decompose_return(stmt: ast.Return, source_lines: list[str]) -> list[str]:
    """Return statement: Enumerate operations, then the return."""
    if stmt.value:
        ret_val = ast.unparse(stmt.value)

        # Extract all operations
        operations = extract_all_operations(stmt.value)

        if operations:
            eis = []
            for op_call in operations:
                call_str = ast.unparse(op_call)
                eis.append(f"{call_str} succeeds")
                eis.append(f"{call_str} raises exception → exception propagates")
            # Final EI: return completes (only if all operations succeed)
            eis.append(f"all operations succeed → returns {ret_val}")
            return eis

        return [f"returns {ret_val}"]
    else:
        return ["returns None"]


def decompose_raise(stmt: ast.Raise, source_lines: list[str]) -> list[str]:
    """Raise statement: 1 EI."""
    if stmt.exc:
        exc = ast.unparse(stmt.exc)
        return [f"raises {exc}"]
    else:
        return ["re-raises current exception"]


def decompose_delete(stmt: ast.Delete, source_lines: list[str]) -> list[str]:
    """Delete statement: 1 EI."""
    targets = ', '.join(ast.unparse(t) for t in stmt.targets)
    return [f"executes: del {targets}"]


def decompose_pass(stmt: ast.Pass, source_lines: list[str]) -> list[str]:
    """Pass statement: 1 EI."""
    return ["executes: pass"]


def decompose_break(stmt: ast.Break, source_lines: list[str]) -> list[str]:
    """Break statement: 1 EI."""
    return ["executes: break"]


def decompose_continue(stmt: ast.Continue, source_lines: list[str]) -> list[str]:
    """Continue statement: 1 EI."""
    return ["executes: continue"]


def decompose_import(stmt: ast.Import, source_lines: list[str]) -> list[str]:
    """Import statement: 1 EI."""
    modules = ', '.join(alias.name for alias in stmt.names)
    return [f"executes: import {modules}"]


def decompose_importfrom(stmt: ast.ImportFrom, source_lines: list[str]) -> list[str]:
    """ImportFrom statement: 1 EI."""
    module = stmt.module or ""
    names = ', '.join(alias.name for alias in stmt.names)
    return [f"executes: from {module} import {names}"]


def decompose_expr(stmt: ast.Expr, source_lines: list[str]) -> list[str]:
    """Expression statement: Enumerate all operations."""
    # Skip docstrings (string literals as the first statement)
    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return []  # Docstrings don't create EIs

    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)

    # Extract all operations
    operations = extract_all_operations(stmt.value)

    if operations:
        eis = []
        for op_call in operations:
            call_str = ast.unparse(op_call)
            eis.append(f"{call_str} succeeds")
            eis.append(f"{call_str} raises exception → exception propagates")
        return eis

    return [f"executes: {line_text}"]


def decompose_global(stmt: ast.Global, source_lines: list[str]) -> list[str]:
    """Global statement: 1 EI."""
    names = ', '.join(stmt.names)
    return [f"executes: global {names}"]


def decompose_nonlocal(stmt: ast.Nonlocal, source_lines: list[str]) -> list[str]:
    """Nonlocal statement: 1 EI."""
    names = ', '.join(stmt.names)
    return [f"executes: nonlocal {names}"]


def decompose_asyncfor(stmt: ast.AsyncFor, source_lines: list[str]) -> list[str]:
    """Async for loop: Same as regular for."""
    return decompose_for(stmt, source_lines)  # type: ignore


def decompose_asyncwith(stmt: ast.AsyncWith, source_lines: list[str]) -> list[str]:
    """Async with statement: Same as regular with."""
    return decompose_with(stmt, source_lines)  # type: ignore


def decompose_default(stmt: ast.stmt, source_lines: list[str]) -> list[str]:
    """Default decomposer for unknown statement types."""
    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)
    return [f"executes: {line_text}"]


# Dispatch table mapping AST node types to decomposer functions
STATEMENT_DECOMPOSERS: dict[type[ast.stmt], Callable[[ast.stmt, list[str]], list[str]]] = {  # type: ignore[dict-item]
    # Conditionals
    ast.If: decompose_if,
    ast.Match: decompose_match,

    # Loops
    ast.For: decompose_for,
    ast.While: decompose_while,

    # Exception handling
    ast.Try: decompose_try,
    ast.With: decompose_with,

    # Assignments
    ast.Assign: decompose_assignment,
    ast.AugAssign: decompose_augassign,
    ast.AnnAssign: decompose_annassign,

    # Imports
    ast.Import: decompose_import,
    ast.ImportFrom: decompose_importfrom,

    # Flow control
    ast.Return: decompose_return,
    ast.Raise: decompose_raise,
    ast.Break: decompose_break,
    ast.Continue: decompose_continue,
    ast.Pass: decompose_pass,

    # Other statements
    ast.Delete: decompose_delete,
    ast.Assert: decompose_assert,
    ast.Expr: decompose_expr,
    ast.Global: decompose_global,
    ast.Nonlocal: decompose_nonlocal,

    # Async variants
    ast.AsyncFor: decompose_asyncfor,
    ast.AsyncWith: decompose_asyncwith,
}


# ============================================================================
# Main Decomposition Function
# ============================================================================

def decompose_statement(stmt: ast.stmt, source_lines: list[str]) -> list[str]:
    """
    Decompose a statement into outcome descriptions (EIs).

    Uses dispatch table to route to appropriate handler.
    Falls back to default handler for unknown statement types.
    """
    decomposer = STATEMENT_DECOMPOSERS.get(type(stmt), decompose_default)
    return decomposer(stmt, source_lines)


# ============================================================================
# AST Traversal
# ============================================================================

def get_all_statements(node: ast.AST) -> list[ast.stmt]:
    """Get all statements in an AST node, including nested ones."""
    statements: list[ast.stmt] = []

    for child in ast.walk(node):
        if isinstance(child, ast.stmt):
            statements.append(child)

    # Sort by line number
    statements.sort(key=lambda s: s.lineno)

    return statements


# ============================================================================
# Result structures
# ============================================================================

class FunctionResult:
    """Result of EI enumeration for a single function."""

    def __init__(self, name: str, line_start: int, line_end: int, branches: list[Branch]) -> None:
        self.name = name
        self.line_start = line_start
        self.line_end = line_end
        self.branches = branches
        self.total_eis = len(branches)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for YAML output."""
        return {
            'name': self.name,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'total_eis': self.total_eis,
            'branches': [b.to_dict() for b in self.branches]
        }


def enumerate_function_eis(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        callable_id
) -> FunctionResult:
    """
    Enumerate all EIs in a function.

    Returns FunctionResult with Branch objects.
    """
    branches: list[Branch] = []
    ei_counter = 1

    # Get all statements in the function (including nested)
    statements = get_all_statements(func_node)

    # Filter to only statements inside this function's line range
    statements = [
        s for s in statements
        if func_node.lineno <= s.lineno <= func_node.end_lineno
    ]

    # Remove the function definition itself
    statements = [s for s in statements if s != func_node]

    for stmt in statements:
        outcomes = decompose_statement(stmt, source_lines)

        if outcomes:  # Skip empty (like docstrings)
            for outcome in outcomes:
                ei_id = generate_ei_id(callable_id, ei_counter)

                # Split outcome into condition and result
                if ' → ' in outcome:
                    condition, result = outcome.split(' → ', 1)
                else:
                    condition = 'executes'
                    result = outcome.replace('executes: ', '')

                branches.append(
                    Branch(
                        id=ei_id,
                        line=stmt.lineno,
                        condition=condition,
                        outcome=result
                    )
                )

                ei_counter += 1

    return FunctionResult(
        name=func_node.name,
        line_start=func_node.lineno,
        line_end=func_node.end_lineno,
        branches=branches
    )


# ============================================================================
# File Processing
# ============================================================================

def enumerate_file(filepath: Path, unit_id: str, function_name: str | None = None) -> list[FunctionResult]:
    """Enumerate EIs for all functions in a file (or just one)."""

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    source_lines = source.split('\n')
    tree = ast.parse(source)

    results: list[FunctionResult] = []
    func_counter = 1

    # Walk the AST to find all functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip if we're looking for a specific function
            if function_name and node.name != function_name:
                continue

            # Generate callable ID using provided unit_id
            callable_id = generate_function_id(unit_id, func_counter)

            result = enumerate_function_eis(node, source_lines, callable_id)
            results.append(result)

            func_counter += 1

    return results


def format_for_yaml(results: list[FunctionResult]) -> dict[str, Any]:
    """Format results as dict for YAML output."""
    if not results:
        return {}

    return {
        'module': "unknown",
        'functions': [r.to_dict() for r in results]
    }


def format_outcome_map_text(result: FunctionResult) -> str:
    """Format the branches for display."""
    lines: list[str] = []
    lines.append(f"=== {result.name} (lines {result.line_start}-{result.line_end}) ===")
    lines.append(f"Total EIs: {result.total_eis}")
    lines.append("")
    lines.append("Execution Items:")

    for branch in result.branches:
        lines.append(f"\n{branch.id} (Line {branch.line}):")
        lines.append(f"  Condition: {branch.condition}")
        lines.append(f"  Outcome: {branch.outcome}")

    return '\n'.join(lines)


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Enumerate Execution Items (EIs) from Python source',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enumerate all functions in a file (YAML output)
  %(prog)s mymodule.py --output mymodule_eis.yaml

  # Enumerate a specific function
  %(prog)s mymodule.py --function validate_typed_dict

  # Human-readable text output
  %(prog)s mymodule.py --text
        """
    )

    parser.add_argument('file', type=Path, help='Python source file')
    parser.add_argument('--unit-id', '-u', required=True, help='Unit ID (required)')
    parser.add_argument('--function', '-f', help='Specific function name to enumerate')
    parser.add_argument('--text', action='store_true', help='Output human-readable text instead of YAML')
    parser.add_argument('--output', '-o', type=Path, help='Save output to file')

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    # Enumerate
    results = enumerate_file(args.file, args.unit_id, args.function)

    if not results:
        if args.function:
            print(f"Error: Function '{args.function}' not found in {args.file}")
        else:
            print(f"Error: No functions found in {args.file}")
        return 1

    # Format output
    if args.text:
        # Human-readable format
        output = '\n\n'.join(format_outcome_map_text(r) for r in results)
    else:
        # YAML format (default for pipeline)
        data = format_for_yaml(results)
        # Set module name from filename
        data['module'] = args.file.stem
        output = yaml.dump(data, sort_keys=False, allow_unicode=True, width=float('inf'))

    # Save or print
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)

    return 0


if __name__ == '__main__':
    exit(main())