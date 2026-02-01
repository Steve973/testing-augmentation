#!/usr/bin/env python3
"""
Execution Item Enumerator - Complete Python Statement Coverage

Enumerates all execution items (EIs) in Python source code.
Outputs YAML format for integration with pipeline.
"""

import argparse
import ast
import yaml
from pathlib import Path
from typing import Any


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
    Assignment: Usually 1 EI.
    Special cases:
    - List/dict/set comprehension: 2-3 EIs
    - Ternary expression: 4 EIs
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

    # Regular assignment
    return [f"executes: {line_text}"]


def decompose_comprehension(comp: ast.comprehension, comp_type: str, empty_repr: str) -> list[str]:
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
    """Return statement: 1 EI."""
    if stmt.value:
        ret_val = ast.unparse(stmt.value)
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


def decompose_expr(stmt: ast.Expr, source_lines: list[str]) -> list[str]:
    """Expression statement (usually function call): 1 EI."""
    # Skip docstrings
    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return []

    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)
    return [f"executes: {line_text}"]


def decompose_global(stmt: ast.Global, source_lines: list[str]) -> list[str]:
    """Global declaration: 1 EI (or skip as non-executable?)."""
    names = ', '.join(stmt.names)
    return [f"executes: global {names}"]


def decompose_nonlocal(stmt: ast.Nonlocal, source_lines: list[str]) -> list[str]:
    """Nonlocal declaration: 1 EI (or skip as non-executable?)."""
    names = ', '.join(stmt.names)
    return [f"executes: nonlocal {names}"]


def decompose_asyncfor(stmt: ast.AsyncFor, source_lines: list[str]) -> list[str]:
    """Async for loop: 2 EIs (0 iterations, ≥1 iterations)."""
    target = ast.unparse(stmt.target)
    iter_expr = ast.unparse(stmt.iter)

    if stmt.orelse:
        return [
            f"async for {target} in {iter_expr}: 0 iterations → else executes",
            f"async for {target} in {iter_expr}: completes without break → else executes",
            f"async for {target} in {iter_expr}: breaks → else skipped"
        ]
    else:
        return [
            f"async for {target} in {iter_expr}: 0 iterations",
            f"async for {target} in {iter_expr}: ≥1 iterations"
        ]


def decompose_asyncwith(stmt: ast.AsyncWith, source_lines: list[str]) -> list[str]:
    """Async with statement: 2 EIs (enters successfully, raises on entry)."""
    contexts = [ast.unparse(item.context_expr) for item in stmt.items]
    context_str = ', '.join(contexts)
    return [
        f"async with {context_str}: enters successfully",
        f"async with {context_str}: raises exception on entry"
    ]


def decompose_default(stmt: ast.stmt, source_lines: list[str]) -> list[str]:
    """Default handler for unknown statement types."""
    line_text = source_lines[stmt.lineno - 1].strip() if stmt.lineno <= len(source_lines) else ast.unparse(stmt)
    return [f"executes: {line_text}"]


# ============================================================================
# Dispatch Table
# ============================================================================

STATEMENT_DECOMPOSERS = {
    # Control flow
    ast.If: decompose_if,
    ast.For: decompose_for,
    ast.While: decompose_while,
    ast.Try: decompose_try,
    ast.With: decompose_with,
    ast.Match: decompose_match,

    # Assignments
    ast.Assign: decompose_assignment,
    ast.AugAssign: decompose_augassign,
    ast.AnnAssign: decompose_annassign,

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
    statements = []

    for child in ast.walk(node):
        if isinstance(child, ast.stmt):
            statements.append(child)

    # Sort by line number
    statements.sort(key=lambda s: s.lineno)

    return statements


def enumerate_function_eis(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        callable_id: str = "C000F001"
) -> dict[str, Any]:
    """
    Enumerate all EIs in a function.

    Returns outcome_map structure with EI IDs.
    """
    branches = []
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
                ei_id = f"{callable_id}E{ei_counter:04d}"

                # Split outcome into condition and result
                if ' → ' in outcome:
                    condition, result = outcome.split(' → ', 1)
                else:
                    condition = 'executes'
                    result = outcome.replace('executes: ', '')

                branches.append({
                    'id': ei_id,
                    'line': stmt.lineno,
                    'condition': condition,
                    'outcome': result
                })

                ei_counter += 1

    return {
        'function': func_node.name,
        'line_start': func_node.lineno,
        'line_end': func_node.end_lineno,
        'branches': branches,
        'total_eis': len(branches)
    }


# ============================================================================
# File Processing
# ============================================================================

def enumerate_file(filepath: Path, function_name: str | None = None) -> list[dict]:
    """Enumerate EIs for all functions in a file (or just one)."""

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    source_lines = source.split('\n')
    tree = ast.parse(source)

    results = []
    func_counter = 1

    # Walk the AST to find all functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip if we're looking for a specific function
            if function_name and node.name != function_name:
                continue

            # Generate callable ID (simplified - just C000F### for now)
            callable_id = f"C000F{func_counter:03d}"

            result = enumerate_function_eis(node, source_lines, callable_id)
            results.append(result)

            func_counter += 1

    return results


def format_for_yaml(results: list[dict]) -> dict:
    """Format results as dict for YAML output."""
    if not results:
        return {}

    return {
        'module': "unknown",
        'functions': [
            {
                'name': r['function'],
                'line_start': r['line_start'],
                'line_end': r['line_end'],
                'total_eis': r['total_eis'],
                'branches': r['branches']  # Now with EI IDs, condition, outcome
            }
            for r in results
        ]
    }


def format_outcome_map_text(result: dict) -> str:
    """Format the branches for display."""
    lines = []
    lines.append(f"=== {result['function']} (lines {result['line_start']}-{result['line_end']}) ===")
    lines.append(f"Total EIs: {result['total_eis']}")
    lines.append("")
    lines.append("Execution Items:")

    for branch in result['branches']:
        lines.append(f"\n{branch['id']} (Line {branch['line']}):")
        lines.append(f"  Condition: {branch['condition']}")
        lines.append(f"  Outcome: {branch['outcome']}")

    return '\n'.join(lines)


# ============================================================================
# CLI
# ============================================================================

def main():
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
    parser.add_argument('--function', '-f', help='Specific function name to enumerate')
    parser.add_argument('--text', action='store_true', help='Output human-readable text instead of YAML')
    parser.add_argument('--output', '-o', type=Path, help='Save output to file')

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    # Enumerate
    results = enumerate_file(args.file, args.function)

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