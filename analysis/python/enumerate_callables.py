#!/usr/bin/env python3
"""Enhanced callable enumerator with complete AST structural analysis."""

from __future__ import annotations

import argparse
import ast
import hashlib
import sys
import yaml
from pathlib import Path
from typing import Any

from models import Branch, TypeRef, ParamSpec, IntegrationCandidate, CallableEntry


# ============================================================================
# CFG and Path Enumeration
# ============================================================================

def build_cfg(branches: list[Branch]) -> dict[str, list[str]]:
    """
    Build control flow graph from branches.

    Exception-raising branches are terminal and don't connect to subsequent lines.

    Returns: adjacency dict {ei_id: [next_ei_ids]}
    """
    if not branches:
        return {}

    # Sort by line number
    sorted_branches = sorted(branches, key=lambda b: b.line)

    # Build adjacency graph
    graph: dict[str, list[str]] = {}

    for i, branch in enumerate(sorted_branches):
        ei_id = branch.id
        current_line = branch.line
        outcome = branch.outcome.lower()

        # Check if this branch raises an exception (terminal)
        is_exception = any(indicator in outcome for indicator in [
            'raises',
            'raise ',
            'exception',
            'error',
            'returns',
            'return ',
            '→ returns',
        ])

        if is_exception:
            # Exception paths terminate - no successors
            graph[ei_id] = []
            continue

        # Find next line's EIs
        next_eis: list[str] = []
        for j in range(i + 1, len(sorted_branches)):
            next_branch = sorted_branches[j]
            if next_branch.line > current_line:
                # This is the next executable line
                next_line = next_branch.line
                next_eis = [
                    b.id for b in sorted_branches
                    if b.line == next_line
                ]
                break

        graph[ei_id] = next_eis

    return graph


def enumerate_paths(
        graph: dict[str, list[str]],
        start_ei: str,
        target_ei: str
) -> list[list[str]]:
    """
    Enumerate all paths from start to target in the CFG.

    Handles same-line branches as alternative paths.
    Uses DFS with cycle detection.
    """

    def dfs(current: str, target: str, path: list[str], visited: set[str]) -> list[list[str]]:
        # Reached target
        if current == target:
            return [path + [current]]

        # Cycle detection
        if current in visited:
            return []

        # Mark visited
        visited_copy = visited | {current}
        all_paths: list[list[str]] = []

        # Explore all successors
        successors = graph.get(current, [])
        if not successors:
            return []

        for next_ei in successors:
            sub_paths = dfs(next_ei, target, path + [current], visited_copy)
            all_paths.extend(sub_paths)

        return all_paths

    # Try from the specified start
    paths = dfs(start_ei, target_ei, [], set())

    # The standalone path should only happen if target IS the start
    if start_ei == target_ei:
        paths = [[target_ei]]

    return paths


def add_execution_paths(entries: list[dict[str, Any]]) -> None:
    """
    Add executionPaths to integration_candidates in all callables.

    Recursively processes all entries and their children.
    """
    print(f"!!!! add_execution_paths CALLED with {len(entries)} entries !!!!")
    for entry in entries:
        # Skip if this has MechanicalOperation decorator
        skip_entry = False
        if entry.get('decorators'):
            for decorator in entry['decorators']:
                if decorator.get('name') == 'MechanicalOperation':
                    # Don't enumerate paths for mechanical operations
                    for integration in entry.get('ast_analysis', {}).get('integration_candidates', []):
                        integration['executionPaths'] = []
                    print(f"!!!! skipped adding execution paths for decorated function !!!!")
                    skip_entry = True
                    break

        if skip_entry:
            continue

        print(f"Processing entry: {entry['name']}")
        print(f"  operation_metadata_decorators: {entry.get('decorators')}")

        # Process this entry if it's a callable with branches and integrations
        if (entry.get('needs_callable_analysis', False) and
                'branches' in entry and
                'ast_analysis' in entry and
                'integration_candidates' in entry['ast_analysis']):

            branches_data = entry['branches']
            integration_candidates = entry['ast_analysis']['integration_candidates']

            if not branches_data or not integration_candidates:
                continue

            # Convert branch dicts to Branch objects for CFG building
            branches = [Branch.from_dict(b) for b in branches_data]

            # Build CFG for this callable
            graph = build_cfg(branches)

            # DEBUG: Print the CFG
            print(f"\n=== CFG for {entry['name']} ===")
            for ei_id, successors in graph.items():
                print(f"  {ei_id} -> {successors}")

            # Find entry points (EIs with no predecessors)
            all_ei_ids = [b.id for b in branches]
            predecessors: dict[str, list[str]] = {ei: [] for ei in all_ei_ids}
            for ei, successors in graph.items():
                for succ in successors:
                    predecessors[succ].append(ei)

            entry_eis = [ei for ei, preds in predecessors.items() if not preds]

            # DEBUG: Print entry points and predecessors
            print(f"\n=== Entry points: {entry_eis} ===")
            print(f"=== Predecessors ===")
            for ei_id, preds in predecessors.items():
                print(f"  {ei_id} <- {preds}")

            # If no entry points found, use first line EIs
            if not entry_eis:
                first_line = min(b.line for b in branches)
                entry_eis = [b.id for b in branches if b.line == first_line]

            # Build line -> EI mapping
            line_to_eis: dict[int, list[str]] = {}
            for branch in branches:
                line = branch.line
                if line not in line_to_eis:
                    line_to_eis[line] = []
                line_to_eis[line].append(branch.id)

            # Enumerate paths for each integration
            for integration in integration_candidates:
                line = integration.get('line')
                if not line or line not in line_to_eis:
                    # Integration has no corresponding EI, set empty paths
                    integration['executionPaths'] = []
                    continue

                integration_eis = line_to_eis[line]
                all_paths: list[list[str]] = []

                # All EIs on same line represent the same integration point
                # Just enumerate to the first EI (they share the same prefix path)
                target_ei = integration_eis[0]
                for start_ei in entry_eis:
                    paths = enumerate_paths(graph, start_ei, target_ei)
                    all_paths.extend(paths)

                # Deduplicate paths
                unique_paths: list[list[str]] = []
                for path in all_paths:
                    if path not in unique_paths:
                        unique_paths.append(path)

                # Attach to integration
                integration['executionPaths'] = unique_paths

        # Recurse into children
        if 'children' in entry and entry['children']:
            add_execution_paths(entry['children'])


# ============================================================================
# AST Visitor for Callable Enumeration
# ============================================================================

class EnhancedCallableEnumerator(ast.NodeVisitor):
    """Enumerate callables with complete structural analysis."""

    def __init__(self, source: str, unit_id: str) -> None:
        self.source = source
        self.unit_id = unit_id
        self.source_lines = source.split('\n')

        self.function_counter = 0
        self.class_counter = 0
        self.nested_counter = 0
        self.method_counters: dict[str, int] = {}

        self.context_stack: list[str] = [unit_id]  # Track current nesting: [unit_id, class_id, method_id, ...]
        self.entries: list[CallableEntry] = []  # Store CallableEntry objects

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition."""
        self.class_counter += 1
        parent_id = self.context_stack[-1]

        # Generate class ID based on nesting depth
        if parent_id == self.unit_id:
            # Top-level class
            class_id = f"{self.unit_id}_C{self.class_counter:03d}"
        else:
            # Nested class - append to parent
            class_id = f"{parent_id}_C{self.class_counter:03d}"

        # Check if this is an enum
        is_enum = any(
            isinstance(base, ast.Name) and base.id == 'Enum'
            for base in node.bases
        )

        entry = CallableEntry(
            id=class_id,
            kind='enum' if is_enum else 'class',
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=self._extract_decorators(node.decorator_list),
            base_classes=[ast.unparse(base) for base in node.bases],
            children=[]
        )

        self.entries.append(entry)

        # Push this class onto context stack
        self.context_stack.append(class_id)

        # Visit methods in this class
        self.method_counters[class_id] = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_method(item, class_id)

        # Pop class from context stack
        self.context_stack.pop()

        # Don't call generic_visit - we've handled children explicitly

    def _visit_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent_id: str) -> None:
        """Visit a method inside a class."""
        self.method_counters[parent_id] += 1
        method_num = self.method_counters[parent_id]
        method_id = f"{parent_id}_M{method_num:03d}"

        # Analyze this method as a callable
        entry = self._analyze_callable(node, method_id, is_method=True)

        # Find parent class in entries and add as child
        for e in self.entries:
            if e.id == parent_id:
                e.children.append(entry)
                break

        # Check for nested functions
        self.context_stack.append(method_id)
        nested_counter = 0
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item != node:
                # This is a nested function
                nested_counter += 1
                self._visit_nested_function(item, method_id)
        self.context_stack.pop()

    def _visit_nested_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent_id: str) -> None:
        """Visit a nested function."""
        # Generate nested function ID
        nested_id = f"{parent_id}_N{self.nested_counter:03d}"
        self.nested_counter += 1

        # Analyze as callable
        entry = self._analyze_callable(node, nested_id, is_method=False)

        # Find parent callable and add as child
        def find_and_add(entries: list[CallableEntry]) -> bool:
            for e in entries:
                if e.id == parent_id:
                    e.children.append(entry)
                    return True
                if e.children and find_and_add(e.children):
                    return True
            return False

        find_and_add(self.entries)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a top-level function definition."""
        # Only process if we're at unit level (not inside a class)
        if len(self.context_stack) > 1:
            return  # Inside a class, handled by _visit_method

        self.function_counter += 1
        func_id = f"{self.unit_id}_F{self.function_counter:03d}"

        entry = self._analyze_callable(node, func_id, is_method=False)
        self.entries.append(entry)

        # Check for nested functions
        self.context_stack.append(func_id)
        self.nested_counter = 0
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item != node:
                self._visit_nested_function(item, func_id)
        self.context_stack.pop()

        # Don't call generic_visit

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition."""
        # Only process if we're at unit level
        if len(self.context_stack) > 1:
            return

        self.function_counter += 1
        func_id = f"{self.unit_id}_F{self.function_counter:03d}"

        entry = self._analyze_callable(node, func_id, is_method=False)
        self.entries.append(entry)

        # Check for nested functions
        self.context_stack.append(func_id)
        self.nested_counter = 0
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item != node:
                self._visit_nested_function(item, func_id)
        self.context_stack.pop()

    def _analyze_callable(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
            callable_id: str,
            is_method: bool
    ) -> CallableEntry:
        """Analyze a callable (function or method) and return CallableEntry object."""

        # Extract signature
        signature = self._build_signature(node)

        # Extract decorators (both regular and operation metadata)
        decorators = self._extract_decorators(node.decorator_list)
        op_metadata_decorators = self._extract_operation_metadata_decorators(node)
        all_decorators = decorators + op_metadata_decorators

        # Extract modifiers
        modifiers = self._extract_modifiers(node)

        # Extract visibility
        visibility = self._extract_visibility(node.name)

        # Extract params with types
        params = self._extract_params(node)

        # Extract return type
        return_type = self._extract_type_ref(node.returns)

        # Find integration candidates
        integration_candidates = self._find_integration_candidates(node)

        return CallableEntry(
            id=callable_id,
            kind='method' if is_method else 'function',
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            needs_callable_analysis=True,
            visibility=visibility,
            signature=signature,
            decorators=all_decorators,
            modifiers=modifiers,
            params=params,
            return_type=return_type,
            integration_candidates=integration_candidates
        )

    def _build_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Build function signature string."""
        try:
            # Get the line containing the function definition
            start_line = node.lineno - 1
            sig_line = self.source_lines[start_line].strip()

            # If signature spans multiple lines, get all of them
            if not sig_line.endswith(':'):
                end_line = start_line
                for i in range(start_line + 1, min(start_line + 20, len(self.source_lines))):
                    sig_line += ' ' + self.source_lines[i].strip()
                    if self.source_lines[i].strip().endswith(':'):
                        break

            # Remove 'def ' and trailing ':'
            sig_line = sig_line.replace('async def ', '').replace('def ', '')
            if sig_line.endswith(':'):
                sig_line = sig_line[:-1].strip()

            return sig_line
        except Exception:
            # Fallback to unparsing
            return f"{node.name}(...)"

    def _extract_decorators(self, decorator_list: list[ast.expr]) -> list[dict[str, Any]]:
        """Extract decorators from AST nodes."""
        decorators: list[dict[str, Any]] = []

        for dec in decorator_list:
            decorator_info: dict[str, Any] = {}

            if isinstance(dec, ast.Name):
                decorator_info['name'] = dec.id
            elif isinstance(dec, ast.Call):
                decorator_info['name'] = ast.unparse(dec.func)
                if dec.args:
                    decorator_info['args'] = [ast.unparse(arg) for arg in dec.args]
                if dec.keywords:
                    decorator_info['kwargs'] = {kw.arg: ast.unparse(kw.value) for kw in dec.keywords if kw.arg}
            else:
                decorator_info['name'] = ast.unparse(dec)

            decorators.append(decorator_info)

        return decorators

    def _extract_operation_metadata_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[
        dict[str, Any]]:
        """Extract operation metadata decorators from comments."""
        decorators: list[dict[str, Any]] = []

        # Check single-line comment before function
        if node.lineno > 1:
            prev_line = self.source_lines[node.lineno - 2].strip()
            if prev_line.startswith('#') and '::' in prev_line:
                decorator = self._parse_decorator_comment(prev_line)
                if decorator:
                    decorators.append(decorator)

        # Check docstring for decorators
        if (node.body and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)):

            docstring = node.body[0].value.value
            for line in docstring.split('\n'):
                line = line.strip()
                if '::' in line:
                    decorator = self._parse_decorator_comment(line)
                    if decorator:
                        decorators.append(decorator)

        return decorators

    def _parse_decorator_comment(self, line: str) -> dict[str, Any] | None:
        """Parse operation metadata decorator from comment line."""
        # Format: # :: DecoratorName | type=value | field=value ...
        if '::' not in line:
            return None

        # Remove comment markers and leading/trailing whitespace
        line = line.lstrip('#').strip()
        if not line.startswith('::'):
            return None

        # Remove :: marker
        line = line[2:].strip()

        # Split by pipe
        parts = [p.strip() for p in line.split('|')]
        if not parts:
            return None

        decorator_name = parts[0]
        kwargs: dict[str, str] = {}

        # Parse field=value pairs
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                kwargs[key.strip()] = value.strip().strip('"').strip("'")

        return {
            'name': decorator_name,
            'kwargs': kwargs
        }

    def _extract_modifiers(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Extract modifiers (async, static, class, property, etc.)."""
        modifiers: list[str] = []

        if isinstance(node, ast.AsyncFunctionDef):
            modifiers.append('async')

        return modifiers

    def _extract_visibility(self, name: str) -> str:
        """Extract visibility from name (public/protected/private)."""
        if name.startswith('__') and not name.endswith('__'):
            return 'private'
        elif name.startswith('_'):
            return 'protected'
        else:
            return 'public'

    def _extract_params(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ParamSpec]:
        """Extract parameter information as ParamSpec objects."""
        params: list[ParamSpec] = []

        for arg in node.args.args:
            param_type = self._extract_type_ref(arg.annotation)
            param = ParamSpec(
                name=arg.arg,
                type=param_type,
                default=None
            )
            params.append(param)

        # Add defaults
        defaults = node.args.defaults
        if defaults:
            num_params = len(params)
            num_defaults = len(defaults)
            start_idx = num_params - num_defaults

            for i, default in enumerate(defaults):
                params[start_idx + i].default = ast.unparse(default)

        return params

    def _extract_type_ref(self, annotation: ast.expr | None) -> TypeRef | None:
        """Extract TypeRef from type annotation."""
        if not annotation:
            return None

        if isinstance(annotation, ast.Name):
            return TypeRef(name=annotation.id)

        if isinstance(annotation, ast.Subscript):
            base_type = ast.unparse(annotation.value)
            args: list[TypeRef] = []

            if isinstance(annotation.slice, ast.Tuple):
                for elt in annotation.slice.elts:
                    arg_ref = self._extract_type_ref(elt)
                    if arg_ref:
                        args.append(arg_ref)
            else:
                arg_ref = self._extract_type_ref(annotation.slice)
                if arg_ref:
                    args.append(arg_ref)

            return TypeRef(name=base_type, args=args)

        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            left_ref = self._extract_type_ref(annotation.left)
            right_ref = self._extract_type_ref(annotation.right)
            args = []
            if left_ref:
                args.append(left_ref)
            if right_ref:
                args.append(right_ref)
            return TypeRef(name='Union', args=args)

        return TypeRef(name=ast.unparse(annotation))

    def _find_integration_candidates(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[IntegrationCandidate]:
        """Find all potential integration points (function/method calls)."""
        candidates: list[IntegrationCandidate] = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                target = self._get_call_target(child)
                if target and target != 'super':  # Skip super() calls
                    candidate = IntegrationCandidate(
                        type='call',
                        target=target,
                        line=child.lineno,
                        signature=ast.unparse(child)
                    )
                    candidates.append(candidate)

        return candidates

    def _get_call_target(self, call_node: ast.Call) -> str | None:
        """Extract the target of a function/method call."""
        try:
            return ast.unparse(call_node.func)
        except Exception:
            return None


# ============================================================================
# ID Generation
# ============================================================================

def generate_unit_id(fully_qualified_name: str) -> str:
    """Generate a unique unit ID from FQN."""
    # Use first 10 chars of SHA256 hash
    hash_obj = hashlib.sha256(fully_qualified_name.encode())
    return f"U{hash_obj.hexdigest()[:10].upper()}"


def derive_fqn(filepath: Path, source_root: Path) -> str:
    """Derive fully qualified name from filepath."""
    try:
        relative = filepath.relative_to(source_root)
    except ValueError:
        # If filepath is not relative to source_root, use absolute
        relative = filepath

    # Remove .py extension and convert path separators to dots
    fqn = str(relative.with_suffix('')).replace('/', '.').replace('\\', '.')

    # Remove __init__ if present
    if fqn.endswith('.__init__'):
        fqn = fqn[:-9]

    return fqn


# ============================================================================
# File Processing
# ============================================================================

def process_file(
        filepath: Path,
        fqn: str,
        output_root: Path,
        ei_root: Path | None = None
) -> dict[str, Any]:
    """Process a Python file and generate inventory."""

    # Read source
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    # Generate unit ID
    unit_id = generate_unit_id(fqn)

    # Parse AST
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return {}

    # Enumerate callables
    enumerator = EnhancedCallableEnumerator(source, unit_id)
    enumerator.entries = []  # Initialize entries list
    enumerator.visit(tree)

    # Convert CallableEntry objects to dicts for downstream processing
    entries = [e.to_dict() for e in enumerator.entries]

    # Load and merge EI data if provided
    if ei_root:
        # Use FQN to construct EI file path (matches Stage 2 output structure)
        ei_file = ei_root / (fqn.replace('.', '/') + '_eis.yaml')

        if ei_file.exists():
            print(f"  → Loading EI data: {ei_file}")
            with open(ei_file, 'r', encoding='utf-8') as f:
                ei_data = yaml.safe_load(f)

            if ei_data and 'functions' in ei_data:
                ei_by_name = {func['name']: func for func in ei_data['functions']}

                def merge_ei_recursive(entries_list: list[dict[str, Any]]) -> None:
                    """Recursively merge EI data into entries."""
                    for entry in entries_list:
                        if entry.get('needs_callable_analysis', False):
                            func_name = entry['name']
                            if func_name in ei_by_name:
                                ei_func = ei_by_name[func_name]
                                entry['branches'] = ei_func.get('branches', [])
                                entry['total_eis'] = ei_func.get('total_eis', 0)

                        # Recurse into children
                        if 'children' in entry and entry['children']:
                            merge_ei_recursive(entry['children'])

                merge_ei_recursive(entries)

    # Add execution paths to integration candidates
    add_execution_paths(entries)

    # Count entries
    def count_all_entries(entries_list: list[dict[str, Any]]) -> int:
        """Recursively count all entries including nested."""
        count = 0
        for entry in entries_list:
            count += 1
            if 'children' in entry and entry['children']:
                count += count_all_entries(entry['children'])
        return count

    total_entries = count_all_entries(entries)

    # Count callables that need analysis
    def count_needs_analysis(entries_list: list[dict[str, Any]]) -> int:
        """Recursively count entries that need callable analysis."""
        count = 0
        for entry in entries_list:
            if entry.get('needs_callable_analysis', False):
                count += 1
            if 'children' in entry and entry['children']:
                count += count_needs_analysis(entry['children'])
        return count

    needs_analysis = count_needs_analysis(entries)

    # Count by kind
    def count_by_kind(entries_list: list[dict[str, Any]]) -> dict[str, int]:
        """Recursively count entries by kind."""
        counts: dict[str, int] = {}
        for entry in entries_list:
            kind = entry['kind']
            counts[kind] = counts.get(kind, 0) + 1
            if 'children' in entry and entry['children']:
                child_counts = count_by_kind(entry['children'])
                for k, v in child_counts.items():
                    counts[k] = counts.get(k, 0) + v
        return counts

    kind_counts = count_by_kind(entries)

    # Build inventory
    inventory: dict[str, Any] = {
        'unit': filepath.stem,
        'fully_qualified_name': fqn,
        'unit_id': unit_id,
        'filepath': str(filepath),
        'language': 'python',
        'entries': entries,
        'summary': {
            'total_entries': total_entries,
            'needs_analysis': needs_analysis,
            'classes': kind_counts.get('class', 0),
            'enums': kind_counts.get('enum', 0),
            'methods': kind_counts.get('method', 0),
            'functions': kind_counts.get('function', 0),
        }
    }

    # Save inventory
    output_path = output_root / (fqn.replace('.', '/') + '.inventory.yaml')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(inventory, f, sort_keys=False, allow_unicode=True, width=float('inf'))

    print(f"  → Unit ID: {unit_id}")
    print(f"  → {total_entries} entries, {needs_analysis} need analysis")
    print(f"  → Saved: {output_path}")

    return inventory


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Enumerate callables from Python source with AST analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--file', type=Path, required=True, help='Python source file')
    parser.add_argument('--fqn', type=str, required=True, help='Fully qualified name')
    parser.add_argument('--output-root', type=Path, default=Path('dist/inventory'),
                        help='Root directory for inventory output')
    parser.add_argument('--ei-root', type=Path, help='Root directory containing EI YAML files')

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    print(f"Processing: {args.file}")
    print(f"  → FQN: {args.fqn}")

    process_file(args.file, args.fqn, args.output_root, args.ei_root)

    return 0


if __name__ == '__main__':
    sys.exit(main())