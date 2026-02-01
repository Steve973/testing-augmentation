#!/usr/bin/env python3
"""Enhanced callable enumerator with complete AST structural analysis."""

import argparse
import ast
import hashlib
import json
import sys
import yaml
from pathlib import Path
from typing import Any


class EnhancedCallableEnumerator(ast.NodeVisitor):
    """Enumerate callables with complete structural analysis."""

    def __init__(self, source: str, unit_id: str):
        self.source = source
        self.unit_id = unit_id
        self.source_lines = source.split('\n')
        self.entries: list[dict[str, Any]] = []
        self.class_counter = 0
        self.function_counter = 0
        self.method_counters: dict[str, int] = {}
        self.nested_counters: dict[str, int] = {}  # Track nested functions per parent
        self.context_stack: list[str] = [unit_id]  # Track current nesting: [unit_id, class_id, method_id, ...]

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

        # Determine if this is an enum
        is_enum = any(
            isinstance(base, ast.Name) and base.id == 'Enum'
            for base in node.bases
        )

        entry = {
            'id': class_id,
            'kind': 'enum' if is_enum else 'class',
            'name': node.name,
            'line_start': node.lineno,
            'line_end': node.end_lineno,
            'needs_callable_analysis': False,
            'parent': parent_id,
            'decorators': self._extract_decorators(node.decorator_list),
            'base_classes': [ast.unparse(base) for base in node.bases],
            'visibility': self._extract_visibility(node.name),
            'children': []
        }

        self.entries.append(entry)

        # Push this class onto context stack
        self.context_stack.append(class_id)

        # Visit methods
        self.method_counters[class_id] = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_method(item, class_id)

        # Pop context before visiting other children
        self.context_stack.pop()

        self.generic_visit(node)

    def _visit_method(self, node: ast.FunctionDef, parent_id: str) -> None:
        """Visit a method inside a class."""
        self.method_counters[parent_id] += 1
        method_id = f"{parent_id}_M{self.method_counters[parent_id]:03d}"

        entry = self._analyze_callable(node, method_id, parent_id, 'method')
        self.entries.append(entry)

        # Update parent's children list
        for e in self.entries:
            if e['id'] == parent_id:
                e['children'].append(method_id)
                break

        # Push method onto context stack to handle nested functions
        self.context_stack.append(method_id)

        # Visit nested functions inside this method
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt, method_id)
            # Recursively check for nested functions in compound statements
            for child in ast.walk(stmt):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != stmt:
                    self._visit_nested_function(child, method_id)

        # Pop method from context stack
        self.context_stack.pop()

    def _visit_nested_function(self, node: ast.FunctionDef, parent_id: str) -> None:
        """Visit a nested function (function defined inside another function/method)."""
        # Initialize counter for this parent if needed
        if parent_id not in self.nested_counters:
            self.nested_counters[parent_id] = 0

        self.nested_counters[parent_id] += 1
        nested_id = f"{parent_id}_N{self.nested_counters[parent_id]:03d}"

        entry = self._analyze_callable(node, nested_id, parent_id, 'function')
        self.entries.append(entry)

        # Update parent's children list
        for e in self.entries:
            if e['id'] == parent_id:
                if 'children' not in e:
                    e['children'] = []
                e['children'].append(nested_id)
                break

        # Push nested function onto context stack for even deeper nesting
        self.context_stack.append(nested_id)

        # Visit even more deeply nested functions
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt, nested_id)
            for child in ast.walk(stmt):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != stmt:
                    self._visit_nested_function(child, nested_id)

        # Pop nested function from context stack
        self.context_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a module-level function."""
        if self._is_method(node):
            self.generic_visit(node)
            return

        self.function_counter += 1
        func_id = f"{self.unit_id}_F{self.function_counter:03d}"

        entry = self._analyze_callable(node, func_id, self.unit_id, 'function')
        self.entries.append(entry)

        # Push function onto context stack
        self.context_stack.append(func_id)

        # Visit nested functions inside this module-level function
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt, func_id)
            for child in ast.walk(stmt):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != stmt:
                    self._visit_nested_function(child, func_id)

        # Pop function from context stack
        self.context_stack.pop()

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function."""
        if self._is_method(node):
            self.generic_visit(node)
            return

        self.function_counter += 1
        func_id = f"{self.unit_id}_F{self.function_counter:03d}"

        entry = self._analyze_callable(node, func_id, self.unit_id, 'function')
        self.entries.append(entry)

        # Push function onto context stack
        self.context_stack.append(func_id)

        # Visit nested functions inside this async function
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt, func_id)
            for child in ast.walk(stmt):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != stmt:
                    self._visit_nested_function(child, func_id)

        # Pop function from context stack
        self.context_stack.pop()

        self.generic_visit(node)

    def _analyze_callable(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
            callable_id: str,
            parent_id: str,
            kind: str
    ) -> dict[str, Any]:
        """Perform complete structural analysis of a callable."""

        # Basic info
        entry = {
            'id': callable_id,
            'kind': kind,
            'name': node.name,
            'line_start': node.lineno,
            'line_end': node.end_lineno,
            'needs_callable_analysis': True,
            'parent': parent_id,
            'visibility': self._extract_visibility(node.name),
        }

        # Signature
        entry['signature'] = self._build_signature(node)

        # Decorators
        entry['decorators'] = self._extract_decorators(node.decorator_list)

        # Operation metadata decorators
        op_metadata = self._extract_operation_metadata_decorators(node)
        if op_metadata:
            entry['operation_metadata_decorators'] = op_metadata

        # Modifiers
        entry['modifiers'] = self._extract_modifiers(node)

        # AST Analysis
        entry['ast_analysis'] = {
            'params': self._extract_params(node),
            'return_type': self._extract_type_ref(node.returns),
            'raises': self._extract_raises(node),
            'structure': self._analyze_structure(node),
            'integration_candidates': self._find_integration_candidates(node),
            'total_executable_lines': self._count_executable_lines(node),
            'estimated_total_eis': self._estimate_total_eis(node)
        }

        return entry

    def _build_signature(self, node: ast.FunctionDef) -> str:
        """Build a signature string from function node."""
        try:
            start_line = node.lineno - 1
            sig_lines = []

            current_line = start_line
            while current_line < len(self.source_lines):
                line = self.source_lines[current_line].strip()
                sig_lines.append(line)
                if line.endswith(':'):
                    break
                current_line += 1

            sig_line = ' '.join(sig_lines)
            sig_line = ' '.join(sig_line.split())

            sig_line = sig_line.replace('async def ', '').replace('def ', '')
            if sig_line.endswith(':'):
                sig_line = sig_line[:-1]

            sig_line = sig_line.replace('( ', '(')
            sig_line = sig_line.replace(' )', ')')
            sig_line = sig_line.replace(', )', ')')

            return sig_line.strip()
        except:
            args = [arg.arg for arg in node.args.args]
            return f"{node.name}({', '.join(args)})"

    def _extract_decorators(self, decorator_list: list[ast.expr]) -> list[dict[str, Any]]:
        """Extract decorator information from AST."""
        decorators = []

        for dec in decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append({'name': dec.id})
            elif isinstance(dec, ast.Call):
                name = ast.unparse(dec.func)
                args = [ast.unparse(arg) for arg in dec.args] if dec.args else None
                kwargs = {kw.arg: ast.unparse(kw.value) for kw in dec.keywords} if dec.keywords else None

                decorator = {'name': name}
                if args:
                    decorator['args'] = args
                if kwargs:
                    decorator['kwargs'] = kwargs
                decorators.append(decorator)
            else:
                decorators.append({'name': ast.unparse(dec)})

        return decorators

    def _extract_operation_metadata_decorators(self, node: ast.FunctionDef) -> list[dict[str, Any]]:
        """Extract operation metadata decorators from comments and docstrings."""
        decorators = []

        if node.lineno > 1:
            prev_line = self.source_lines[node.lineno - 2].strip()
            if prev_line.startswith('#') and '::' in prev_line:
                decorator = self._parse_decorator_comment(prev_line)
                if decorator:
                    decorators.append(decorator)

        docstring = ast.get_docstring(node)
        if docstring:
            for line in docstring.split('\n'):
                line = line.strip()
                if '::' in line:
                    decorator = self._parse_decorator_comment(line)
                    if decorator:
                        decorators.append(decorator)

        return decorators

    def _parse_decorator_comment(self, line: str) -> dict[str, Any] | None:
        """Parse operation metadata decorator from comment line."""
        line = line.lstrip('#').strip()

        if not line.startswith('::'):
            return None

        line = line[2:].strip()
        parts = [p.strip() for p in line.split('|')]

        if not parts:
            return None

        name = parts[0]
        kwargs = {}

        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()

                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                kwargs[key] = value

        return {
            'name': name,
            'kwargs': kwargs
        }

    def _extract_modifiers(self, node: ast.FunctionDef) -> list[str]:
        """Extract function/method modifiers."""
        modifiers = []

        if isinstance(node, ast.AsyncFunctionDef):
            modifiers.append('async')

        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                if dec.id in ['staticmethod', 'classmethod', 'property']:
                    modifiers.append(dec.id)

        return modifiers

    def _extract_visibility(self, name: str) -> str:
        """Extract visibility based on Python naming conventions."""
        if name.startswith('__') and not name.endswith('__'):
            return 'private'
        elif name.startswith('_'):
            return 'protected'
        else:
            return 'public'

    def _extract_params(self, node: ast.FunctionDef) -> list[dict[str, Any]]:
        """Extract parameter information."""
        params = []

        for arg in node.args.args:
            param = {'name': arg.arg}

            if arg.annotation:
                param['type'] = self._extract_type_ref(arg.annotation)

            params.append(param)

        defaults = node.args.defaults
        if defaults:
            num_params = len(params)
            num_defaults = len(defaults)
            start_idx = num_params - num_defaults

            for i, default in enumerate(defaults):
                params[start_idx + i]['default'] = ast.unparse(default)

        return params

    def _extract_type_ref(self, annotation: ast.expr | None) -> dict[str, Any] | None:
        """Extract TypeRef from type annotation."""
        if not annotation:
            return None

        if isinstance(annotation, ast.Name):
            return {'name': annotation.id}

        if isinstance(annotation, ast.Subscript):
            base_type = ast.unparse(annotation.value)
            args = []

            if isinstance(annotation.slice, ast.Tuple):
                for elt in annotation.slice.elts:
                    args.append(self._extract_type_ref(elt))
            else:
                args.append(self._extract_type_ref(annotation.slice))

            result = {'name': base_type}
            if args:
                result['args'] = args
            return result

        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            return {
                'name': 'Union',
                'args': [
                    self._extract_type_ref(annotation.left),
                    self._extract_type_ref(annotation.right)
                ]
            }

        return {'name': ast.unparse(annotation)}

    def _extract_raises(self, node: ast.FunctionDef) -> list[dict[str, Any]]:
        """Find all raise statements in function body."""
        raises = []
        seen = set()

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Raise):
                if stmt.exc:
                    exc_type = None
                    if isinstance(stmt.exc, ast.Call):
                        exc_type = ast.unparse(stmt.exc.func)
                    elif isinstance(stmt.exc, ast.Name):
                        exc_type = stmt.exc.id

                    if exc_type and exc_type not in seen:
                        seen.add(exc_type)
                        raises.append({
                            'name': exc_type,
                            'line': stmt.lineno
                        })

        return raises

    def _analyze_structure(self, node: ast.FunctionDef) -> dict[int, dict[str, Any]]:
        """Analyze line-by-line structure and EI counts."""
        structure = {}

        for stmt in ast.walk(node):
            if not hasattr(stmt, 'lineno'):
                continue

            line = stmt.lineno

            if line in structure:
                continue

            analysis = self._analyze_statement(stmt)
            if analysis:
                structure[line] = analysis

        return structure

    def _analyze_statement(self, stmt: ast.stmt) -> dict[str, Any] | None:
        """Analyze a single statement for EI count and type."""

        if isinstance(stmt, ast.If):
            return {
                'type': 'If',
                'ei_count': 2,
                'hint': 'if statement: true/false branches'
            }

        if isinstance(stmt, ast.For):
            return {
                'type': 'For',
                'ei_count': 2,
                'hint': 'for loop: 0 iterations / ≥1 iterations'
            }

        if isinstance(stmt, ast.While):
            return {
                'type': 'While',
                'ei_count': 2,
                'hint': 'while loop: initial condition true/false'
            }

        if isinstance(stmt, ast.Try):
            num_handlers = len(stmt.handlers)
            return {
                'type': 'Try',
                'ei_count': 1 + num_handlers,
                'handlers': num_handlers,
                'hint': f'try with {num_handlers} exception handler(s)'
            }

        if isinstance(stmt, ast.Match):
            num_cases = len(stmt.cases)
            return {
                'type': 'Match',
                'ei_count': num_cases,
                'hint': f'match with {num_cases} cases'
            }

        if isinstance(stmt, ast.Assign):
            if isinstance(stmt.value, ast.ListComp):
                comp = stmt.value
                has_filter = any(gen.ifs for gen in comp.generators)
                return {
                    'type': 'ListComp',
                    'ei_count': 3 if has_filter else 2,
                    'has_filter': has_filter,
                    'hint': 'list comprehension with filter: empty/all-filtered/some-pass' if has_filter else 'list comprehension: empty/has-items'
                }

            if isinstance(stmt.value, ast.DictComp):
                comp = stmt.value
                has_filter = any(gen.ifs for gen in comp.generators)
                return {
                    'type': 'DictComp',
                    'ei_count': 3 if has_filter else 2,
                    'has_filter': has_filter,
                    'hint': 'dict comprehension'
                }

            if isinstance(stmt.value, ast.SetComp):
                comp = stmt.value
                has_filter = any(gen.ifs for gen in comp.generators)
                return {
                    'type': 'SetComp',
                    'ei_count': 3 if has_filter else 2,
                    'has_filter': has_filter,
                    'hint': 'set comprehension'
                }

        if isinstance(stmt, ast.Raise):
            return {
                'type': 'Raise',
                'ei_count': 1,
                'hint': 'raise statement'
            }

        if isinstance(stmt, ast.Return):
            return {
                'type': 'Return',
                'ei_count': 1,
                'hint': 'return statement'
            }

        if isinstance(stmt, ast.With):
            return {
                'type': 'With',
                'ei_count': 2,
                'hint': 'with statement: enters successfully / raises on entry'
            }

        if isinstance(stmt, ast.Expr):
            if isinstance(stmt.value, ast.Call):
                target = self._get_call_target(stmt.value)
                return {
                    'type': 'Call',
                    'ei_count': 1,
                    'target': target,
                    'hint': f'function/method call: {target}'
                }

        return {
            'type': type(stmt).__name__,
            'ei_count': 1,
            'hint': 'simple statement'
        }

    def _find_integration_candidates(self, node: ast.FunctionDef) -> list[dict[str, Any]]:
        """Find all potential integration points (calls, imports)."""
        candidates = []

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                target = self._get_call_target(stmt)

                if target:
                    candidates.append({
                        'type': 'call',
                        'target': target,
                        'line': stmt.lineno,
                        'signature': ast.unparse(stmt)
                    })

        return candidates

    def _get_call_target(self, call_node: ast.Call) -> str | None:
        """Extract the target of a function/method call."""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return ast.unparse(call_node.func)
        return None

    def _count_executable_lines(self, node: ast.FunctionDef) -> int:
        """Count executable lines in function."""
        lines = set()
        for stmt in ast.walk(node):
            if hasattr(stmt, 'lineno'):
                lines.add(stmt.lineno)
        return len(lines)

    def _estimate_total_eis(self, node: ast.FunctionDef) -> int:
        """Estimate total EI count for function."""
        structure = self._analyze_structure(node)
        return sum(info['ei_count'] for info in structure.values())

    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if function is actually a method inside a class."""
        return False


def generate_unit_id(fully_qualified_name: str) -> str:
    """Generate unit ID from fully qualified name using SHA256 hash."""
    hash_digest = hashlib.sha256(fully_qualified_name.encode()).hexdigest()
    return "U" + hash_digest[:10].upper()


def derive_fqn(filepath: Path, source_root: Path) -> str:
    """Derive fully qualified name from file path relative to source root."""
    try:
        rel_path = filepath.relative_to(source_root)
    except ValueError:
        raise ValueError(f"File {filepath} is not under source root {source_root}")

    module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
    fqn = '.'.join(module_parts)

    return fqn


def restructure_hierarchically(entries: list[dict], unit_id: str, unit_name: str) -> list[dict]:
    """
    Restructure flat entry list into hierarchical structure.

    Classes contain their methods as nested 'children' entries.
    Returns a single unit entry containing all top-level entries as children.
    """
    # Build lookup by ID
    entries_by_id = {e['id']: e for e in entries}

    # Build map of parent to children (full entry objects, not IDs)
    children_by_parent = {}
    for entry in entries:
        parent_id = entry.get('parent')
        if parent_id and parent_id != entry['id']:
            if parent_id not in children_by_parent:
                children_by_parent[parent_id] = []
            # DON'T delete parent yet - we need it for filtering
            children_by_parent[parent_id].append(entry)

    print(f"DEBUG restructure: children_by_parent has {len(children_by_parent)} parents")
    for parent_id, children in list(children_by_parent.items())[:3]:
        print(f"  {parent_id}: {len(children)} children - {[c['id'] for c in children]}")

    # Replace children ID lists with actual entry objects
    for entry in entries:
        if entry['id'] in children_by_parent:
            old_children = entry.get('children', [])
            new_children = children_by_parent[entry['id']]
            print(f"DEBUG restructure: Replacing children for {entry['id']}")
            print(f"  Old (type={type(old_children)}): {old_children[:2] if len(old_children) > 0 else []}")
            print(f"  New (type={type(new_children)}): {[c['id'] for c in new_children[:2]]}")
            entry['children'] = new_children
        elif 'children' in entry and entry['children']:
            # If entry has children but they're not in our map, clear them
            print(f"DEBUG restructure: Clearing orphan children for {entry['id']}: {entry['children']}")
            entry['children'] = []

    # Return only top-level entries (parent is the unit_id or no parent)
    top_level = []
    for entry in entries:
        parent_id = entry.get('parent')
        # Top level if: no parent OR parent equals unit_id
        if not parent_id or parent_id == unit_id:
            # NOW remove 'parent' field from top-level entries
            if 'parent' in entry:
                del entry['parent']
            top_level.append(entry)
        else:
            # Also remove parent from nested children
            if 'parent' in entry:
                del entry['parent']

    # Create unit entry that contains all top-level entries
    unit_entry = {
        'id': unit_id,
        'kind': 'unit',
        'name': unit_name,
        'children': top_level
    }

    return [unit_entry]


def enumerate_callables(
        filepath: Path,
        fully_qualified_name: str,
        ei_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Enumerate all callables in a Python file with full structural analysis."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source, filename=str(filepath))

    unit_id = generate_unit_id(fully_qualified_name)

    enumerator = EnhancedCallableEnumerator(source, unit_id)
    enumerator.visit(tree)

    entries = sorted(enumerator.entries, key=lambda e: e['line_start'])

    print(f"DEBUG: Before restructure: {len(entries)} entries")
    for e in entries[:5]:
        print(f"  {e['id']} parent={e.get('parent')}")

    # Restructure into hierarchy (methods under classes)
    entries = restructure_hierarchically(entries, unit_id, filepath.stem)

    print(f"DEBUG: After restructure: {len(entries)} entries")
    for e in entries:
        children = e.get('children', [])
        if children:
            print(f"  {e['id']} - children: {type(children)} with {len(children)} items")
            if len(children) > 0:
                child_types = [type(c) for c in children]
                if all(isinstance(c, dict) for c in children):
                    print(f"    All children are dicts: {[c['id'] for c in children]}")
                else:
                    print(f"    MIXED TYPES: {child_types}")
                    print(f"    Values: {children}")
        else:
            print(f"  {e['id']} - no children")

    # Always promote ast_analysis fields to top level
    def promote_fields_recursive(entries_list):
        """Recursively promote ast_analysis fields to top level."""
        for i, entry in enumerate(entries_list):
            try:
                if entry.get('needs_callable_analysis', False):
                    # Promote ast_analysis data to top level
                    if 'ast_analysis' in entry:
                        ast_data = entry['ast_analysis']

                        # Promote params
                        if 'params' in ast_data:
                            entry['params'] = ast_data['params']

                        # Promote return_type
                        if 'return_type' in ast_data and ast_data['return_type']:
                            entry['returnType'] = ast_data['return_type']

                        # Promote raises
                        if 'raises' in ast_data and ast_data['raises']:
                            entry['raises'] = ast_data['raises']

                # Recurse into children
                if 'children' in entry and entry['children']:
                    promote_fields_recursive(entry['children'])
            except AttributeError as e:
                print(f"ERROR in promote_fields_recursive - entry {i}")
                print(f"  Error: {e}")
                print(f"  entry type: {type(entry)}")
                if isinstance(entry, dict):
                    print(f"  entry id: {entry.get('id', 'NO ID')}")
                    print(f"  entry children: {entry.get('children', 'NO CHILDREN')}")
                else:
                    print(f"  entry value: {entry}")
                raise

    print("DEBUG: About to call promote_fields_recursive")
    promote_fields_recursive(entries)
    print("DEBUG: promote_fields_recursive completed")

    # Merge EI data if provided
    if ei_data and 'functions' in ei_data:
        ei_by_name = {func['name']: func for func in ei_data['functions']}

        def merge_ei_recursive(entries_list):
            """Recursively merge EI data into entries."""
            for i, entry in enumerate(entries_list):
                try:
                    if entry.get('needs_callable_analysis', False):
                        func_name = entry['name']
                        if func_name in ei_by_name:
                            ei_func = ei_by_name[func_name]
                            entry['branches'] = ei_func.get('branches', [])
                            entry['total_eis'] = ei_func.get('total_eis', 0)

                    # Recurse into children
                    if 'children' in entry and entry['children']:
                        merge_ei_recursive(entry['children'])
                except AttributeError as e:
                    print(f"ERROR in merge_ei_recursive - entry {i}")
                    print(f"  Error: {e}")
                    print(f"  entry type: {type(entry)}")
                    if isinstance(entry, dict):
                        print(f"  entry id: {entry.get('id', 'NO ID')}")
                    else:
                        print(f"  entry value: {entry}")
                    raise

        merge_ei_recursive(entries)
        print("DEBUG: merge_ei_recursive completed")

    def count_all_entries(entries_list):
        """Recursively count all entries including nested."""
        count = 0
        for i, entry in enumerate(entries_list):
            try:
                count += 1
                if 'children' in entry and entry['children']:
                    count += count_all_entries(entry['children'])
            except (AttributeError, TypeError) as e:
                print(f"ERROR in count_all_entries - entry {i}")
                print(f"  Error: {e}")
                print(f"  entry type: {type(entry)}")
                raise
        return count

    def collect_needs_analysis(entries_list):
        """Recursively collect all entries needing analysis."""
        result = []
        for i, entry in enumerate(entries_list):
            try:
                if entry.get('needs_callable_analysis', False):
                    result.append(entry)
                if 'children' in entry and entry['children']:
                    result.extend(collect_needs_analysis(entry['children']))
            except (AttributeError, TypeError) as e:
                print(f"ERROR in collect_needs_analysis - entry {i}")
                print(f"  Error: {e}")
                print(f"  entry type: {type(entry)}")
                raise
        return result

    needs_analysis = collect_needs_analysis(entries)
    print(f"DEBUG: collect_needs_analysis completed - found {len(needs_analysis)} callables")

    # Calculate total EIs
    total_eis = sum(e.get('total_eis', 0) for e in needs_analysis)

    # Count integrations (if present in AST analysis)
    # Note: integration_candidates is a flat list, not categorized yet
    total_integration_candidates = 0

    for entry in needs_analysis:
        if 'ast_analysis' in entry and 'integration_candidates' in entry['ast_analysis']:
            candidates = entry['ast_analysis']['integration_candidates']
            if isinstance(candidates, list):
                total_integration_candidates += len(candidates)

    print("DEBUG: Integration counting completed")

    # For now, we don't have categorized integration counts
    # These will be 0 until classification happens in a later stage
    interunit_count = 0
    extlib_count = 0
    boundary_count = 0

    def count_by_kind(entries_list, kind):
        """Recursively count entries of a specific kind."""
        count = 0
        for entry in entries_list:
            if entry['kind'] == kind:
                count += 1
            if 'children' in entry and entry['children']:
                count += count_by_kind(entry['children'], kind)
        return count

    print("DEBUG: About to build return dict with summary")

    return {
        'unit': filepath.stem,
        'fully_qualified_name': fully_qualified_name,
        'unit_id': unit_id,
        'filepath': str(filepath),
        'language': 'python',
        'entries': entries,
        'summary': {
            'total_entries': count_all_entries(entries),
            'needs_analysis': len(needs_analysis),
            'classes': count_by_kind(entries, 'class'),
            'enums': count_by_kind(entries, 'enum'),
            'methods': count_by_kind(entries, 'method'),
            'functions': count_by_kind(entries, 'function'),
            'callables_analyzed': len(needs_analysis),
            'total_eis': total_eis,
            'interunit_integrations': interunit_count,
            'extlib_integrations': extlib_count,
            'boundary_integrations': boundary_count,
        }
    }


def process_file(
        filepath: Path,
        fqn: str,
        output_root: Path,
        source_root: Path | None = None,
        ei_root: Path | None = None
) -> dict[str, Any]:
    """Process a single file and save inventory."""
    print(f"Processing: {filepath}")
    print(f"  → FQN: {fqn}")

    # Load EI data if available
    ei_data = None
    if ei_root:
        if source_root:
            try:
                rel_path = filepath.relative_to(source_root)
                ei_file = ei_root / rel_path.parent / f"{filepath.stem}_eis.yaml"
            except ValueError:
                ei_file = ei_root / f"{filepath.stem}_eis.yaml"
        else:
            ei_file = ei_root / f"{filepath.stem}_eis.yaml"

        if ei_file.exists():
            print(f"  → Loading EI data: {ei_file}")
            with open(ei_file, 'r', encoding='utf-8') as f:
                ei_data = yaml.safe_load(f)

    inventory = enumerate_callables(filepath, fqn, ei_data)

    print(f"  → Unit ID: {inventory['unit_id']}")
    print(f"  → {inventory['summary']['total_entries']} entries, "
          f"{inventory['summary']['needs_analysis']} need analysis")

    if source_root:
        try:
            rel_path = filepath.relative_to(source_root)
            output_file = output_root / rel_path.parent / f"{filepath.stem}.inventory.yaml"
        except ValueError:
            output_file = output_root / f"{filepath.stem}.inventory.yaml"
    else:
        output_file = output_root / f"{filepath.stem}.inventory.yaml"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(inventory, f, sort_keys=False, allow_unicode=True, width=float('inf'))

    print(f"  → Saved: {output_file}")
    print()

    return inventory


def process_directory(
        source_root: Path,
        output_root: Path,
        ei_root: Path | None = None
) -> list[dict[str, Any]]:
    """Process all Python files in a directory tree."""
    inventories = []

    py_files = [
        f for f in source_root.rglob("*.py")
        if f.name != "__init__.py"
    ]

    print(f"Found {len(py_files)} Python files to process\n")

    for filepath in sorted(py_files):
        fqn = derive_fqn(filepath, source_root)

        try:
            inventory = process_file(filepath, fqn, output_root, source_root, ei_root)
            inventories.append(inventory)
        except Exception as e:
            print(f"  ✗ Error processing {filepath}: {e}\n")

    return inventories


def main():
    parser = argparse.ArgumentParser(
        description="Enumerate callables in Python modules with AST analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file with manual FQN
  %(prog)s --file compatibility.py --fqn project.internal.compatibility

  # Single file with auto FQN
  %(prog)s --file src/project/internal/compatibility.py --project-root .

  # Batch process (default source root: src/)
  %(prog)s --project-root .
  %(prog)s .

  # Batch process with custom source root
  %(prog)s --project-root . --source-root project_resolution_engine
        """
    )

    parser.add_argument(
        'project_root',
        nargs='?',
        type=Path,
        help='Project root directory (enables batch mode)'
    )
    parser.add_argument(
        '--file',
        type=Path,
        help='Process single file'
    )
    parser.add_argument(
        '--fqn',
        type=str,
        help='Fully qualified name (required with --file if no --project-root)'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        help='Project root directory (enables auto-FQN derivation)'
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
        default='dist/inventory',
        help='Output root (default: "dist/inventory")'
    )
    parser.add_argument(
        '--ei-root',
        type=str,
        default='dist/eis',
        help='EI data root (default: "dist/eis")'
    )

    args = parser.parse_args()

    project_root = args.project_root or args.project_root

    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)

        if project_root:
            source_root = project_root / args.source_root
            if not source_root.exists():
                print(f"Error: Source root not found: {source_root}")
                sys.exit(1)

            fqn = derive_fqn(args.file, source_root)
            output_root = project_root / args.output_root
            ei_root = project_root / args.ei_root
        elif args.fqn:
            fqn = args.fqn
            source_root = None
            output_root = Path(args.output_root)
            ei_root = Path(args.ei_root)
        else:
            print("Error: --fqn required with --file if no --project-root specified")
            sys.exit(1)

        process_file(args.file, fqn, output_root, source_root, ei_root)

    elif project_root:
        source_root = project_root / args.source_root

        if not source_root.exists():
            print(f"Error: Source root not found: {source_root}")
            print(f"  Looking for: {source_root}")
            print(f"  Hint: Use --source-root to specify a different source directory")
            sys.exit(1)

        output_root = project_root / args.output_root
        ei_root = project_root / args.ei_root

        print(f"{'=' * 70}")
        print(f"Batch Processing")
        print(f"{'=' * 70}")
        print(f"Project root:  {project_root.absolute()}")
        print(f"Source root:   {source_root.absolute()}")
        print(f"Output root:   {output_root.absolute()}")
        print(f"EI root:       {ei_root.absolute()}")
        print(f"{'=' * 70}\n")

        inventories = process_directory(source_root, output_root, ei_root)

        print(f"{'=' * 70}")
        print(f"Summary")
        print(f"{'=' * 70}")
        print(f"Processed:         {len(inventories)} modules")
        print(f"Total entries:     {sum(i['summary']['total_entries'] for i in inventories)}")
        print(f"Total callables:   {sum(i['summary']['needs_analysis'] for i in inventories)}")
        print(f"  - Functions:     {sum(i['summary']['functions'] for i in inventories)}")
        print(f"  - Methods:       {sum(i['summary']['methods'] for i in inventories)}")
        print(f"Container entries: {sum(i['summary']['classes'] + i['summary']['enums'] for i in inventories)}")
        print(f"  - Classes:       {sum(i['summary']['classes'] for i in inventories)}")
        print(f"  - Enums:         {sum(i['summary']['enums'] for i in inventories)}")
        print(f"{'=' * 70}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()