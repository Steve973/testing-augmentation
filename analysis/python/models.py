#!/usr/bin/env python3
"""
Shared data models for the unit ledger analysis pipeline.

These models define contracts between pipeline stages:
- enumerate_callables.py (Stage 1)
- enumerate_exec_items.py (Stage 2)  
- CFG path enumeration (Stage 3)
- Ledger transformation (Stage 4)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# =============================================================================
# Common Types
# =============================================================================

@dataclass
class TypeRef:
    """
    Type reference with optional generic arguments.

    Examples:
        int -> TypeRef(name='int')
        list[str] -> TypeRef(name='list', args=[TypeRef(name='str')])
        dict[str, Any] -> TypeRef(name='dict', args=[TypeRef(name='str'), TypeRef(name='Any')])
    """
    name: str
    args: list[TypeRef] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TypeRef | None:
        """Parse from inventory dict format."""
        if not data:
            return None
        return cls(
            name=data['name'],
            args=[cls.from_dict(arg) for arg in data.get('args', []) if arg is not None]
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to inventory dict format."""
        result: dict[str, Any] = {'name': self.name}
        if self.args:
            result['args'] = [arg.to_dict() for arg in self.args]
        return result


@dataclass
class ParamSpec:
    """Parameter specification."""
    name: str
    type: TypeRef | None = None
    default: str | None = None  # Store as string representation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParamSpec:
        """Parse from inventory dict format."""
        return cls(
            name=data['name'],
            type=TypeRef.from_dict(data['type']) if 'type' in data else None,
            default=data.get('default')
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to inventory dict format."""
        result: dict[str, Any] = {'name': self.name}
        if self.type:
            result['type'] = self.type.to_dict()
        if self.default is not None:
            result['default'] = self.default
        return result


# =============================================================================
# Execution Items (Branches)
# =============================================================================

@dataclass
class Branch:
    """
    Execution Item (EI) representation.

    Contract between enumerate_exec_items.py and downstream stages.
    Called "Branch" in current code but represents an Execution Item.
    """
    id: str
    line: int
    condition: str
    outcome: str

    def __post_init__(self) -> None:
        """Validate branch structure."""
        if not self.id:
            raise ValueError("Branch ID cannot be empty")
        if self.line <= 0:
            raise ValueError(f"Invalid line number: {self.line}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Branch:
        """Parse from inventory dict format."""
        return cls(
            id=data['id'],
            line=data['line'],
            condition=data['condition'],
            outcome=data['outcome']
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to inventory dict format."""
        return {
            'id': self.id,
            'line': self.line,
            'condition': self.condition,
            'outcome': self.outcome
        }

    def to_ledger_ei_spec(self) -> dict[str, str]:
        """
        Transform to ledger EiSpec format.

        Ledger format uses the same structure but may add additional fields.
        """
        return {
            'id': self.id,
            'condition': self.condition,
            'outcome': self.outcome
        }


# =============================================================================
# Integration Points
# =============================================================================

class IntegrationType(str, Enum):
    """Type of integration point."""
    CALL = 'call'
    CONSTRUCT = 'construct'
    IMPORT = 'import'
    DISPATCH = 'dispatch'
    IO = 'io'
    OTHER = 'other'


class IntegrationCategory(str, Enum):
    """Category of integration after classification."""
    INTERUNIT = 'interunit'
    EXTLIB = 'extlib'
    BOUNDARY = 'boundaries'
    UNKNOWN = 'unknown'


@dataclass
class IntegrationCandidate:
    """
    Integration point before categorization.

    Contract between enumerate_callables.py (Stage 1) and CFG enumeration (Stage 3).
    Stage 3 populates the execution_paths field.
    """
    type: str  # IntegrationType value
    target: str
    line: int
    signature: str
    execution_paths: list[list[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate integration candidate."""
        if not self.target:
            raise ValueError("Integration target cannot be empty")
        if self.line <= 0:
            raise ValueError(f"Invalid line number: {self.line}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationCandidate:
        """Parse from inventory dict format."""
        return cls(
            type=data['type'],
            target=data['target'],
            line=data['line'],
            signature=data['signature'],
            execution_paths=data.get('executionPaths', [])
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to inventory dict format."""
        result: dict[str, Any] = {
            'type': self.type,
            'target': self.target,
            'line': self.line,
            'signature': self.signature
        }
        if self.execution_paths:
            result['executionPaths'] = self.execution_paths
        return result

    def to_ledger_integration_fact(self) -> dict[str, Any]:
        """
        Transform to ledger IntegrationFact format.

        Returns:
            dict in ledger IntegrationFact format
        """
        # Generate integration ID from the last EI in the first path
        integration_id: str | None = None
        if self.execution_paths and self.execution_paths[0]:
            last_ei = self.execution_paths[0][-1]
            integration_id = f"I{last_ei}"

        fact: dict[str, Any] = {}

        # ID must be first (if present)
        if integration_id:
            fact['id'] = integration_id

        # Then required fields
        fact['target'] = self.target
        fact['kind'] = self.type
        fact['signature'] = self.signature
        fact['executionPaths'] = self.execution_paths

        return fact


# =============================================================================
# Callable Entries
# =============================================================================

@dataclass
class CallableEntry:
    """
    Entry for any code element (unit, class, enum, function, method).

    Central data structure that flows through all pipeline stages.
    Can represent both callable entries (functions/methods) and
    non-callable entries (classes/enums) via the 'kind' field.
    """
    id: str
    kind: str  # 'unit', 'class', 'enum', 'function', 'method'
    name: str
    line_start: int
    line_end: int
    signature: str | None = None
    visibility: str | None = None  # 'public', 'protected', 'private'
    decorators: list[dict[str, Any]] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)  # ['async', 'static', etc.]
    base_classes: list[str] = field(default_factory=list)  # For classes/enums
    children: list[CallableEntry] = field(default_factory=list)  # Nested classes/methods
    params: list[ParamSpec] = field(default_factory=list)
    return_type: TypeRef | None = None
    branches: list[Branch] = field(default_factory=list)
    integration_candidates: list[IntegrationCandidate] = field(default_factory=list)
    total_eis: int = 0
    needs_callable_analysis: bool = False  # True for functions/methods

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CallableEntry:
        """
        Parse from inventory dict format.

        Handles both pre-EI and post-EI merge states.
        """
        # Extract params from ast_analysis if present
        params: list[ParamSpec] = []
        if 'params' in data:
            params = [ParamSpec.from_dict(p) for p in data['params']]
        elif 'ast_analysis' in data and 'params' in data['ast_analysis']:
            params = [ParamSpec.from_dict(p) for p in data['ast_analysis']['params']]

        # Extract return type
        return_type: TypeRef | None = None
        if 'returnType' in data:
            return_type = TypeRef.from_dict(data['returnType'])
        elif 'ast_analysis' in data and 'return_type' in data['ast_analysis']:
            return_type = TypeRef.from_dict(data['ast_analysis']['return_type'])

        # Extract branches (EIs)
        branches = [Branch.from_dict(b) for b in data.get('branches', [])]

        # Extract integration candidates
        integration_candidates: list[IntegrationCandidate] = []
        if 'ast_analysis' in data and 'integration_candidates' in data['ast_analysis']:
            integration_candidates = [
                IntegrationCandidate.from_dict(ic)
                for ic in data['ast_analysis']['integration_candidates']
            ]

        # Extract children (recursive)
        children = [cls.from_dict(c) for c in data.get('children', [])]

        return cls(
            id=data['id'],
            kind=data['kind'],
            name=data['name'],
            line_start=data.get('line_start', 0),
            line_end=data.get('line_end', 0),
            signature=data.get('signature'),
            visibility=data.get('visibility'),
            decorators=data.get('decorators', []),
            modifiers=data.get('modifiers', []),
            base_classes=data.get('base_classes', []),
            children=children,
            params=params,
            return_type=return_type,
            branches=branches,
            integration_candidates=integration_candidates,
            total_eis=data.get('total_eis', len(branches)),
            needs_callable_analysis=data.get('needs_callable_analysis', False)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to inventory dict format."""
        result: dict[str, Any] = {
            'id': self.id,
            'kind': self.kind,
            'name': self.name,
            'line_start': self.line_start,
            'line_end': self.line_end
        }

        if self.signature:
            result['signature'] = self.signature

        if self.visibility:
            result['visibility'] = self.visibility

        if self.decorators:
            result['decorators'] = self.decorators

        if self.modifiers:
            result['modifiers'] = self.modifiers

        if self.base_classes:
            result['base_classes'] = self.base_classes

        if self.children:
            result['children'] = [c.to_dict() for c in self.children]

        if self.needs_callable_analysis:
            result['needs_callable_analysis'] = self.needs_callable_analysis

        if self.params:
            result['params'] = [p.to_dict() for p in self.params]

        if self.return_type:
            result['returnType'] = self.return_type.to_dict()

        if self.branches:
            result['branches'] = [b.to_dict() for b in self.branches]
            result['total_eis'] = len(self.branches)

        if self.integration_candidates:
            result['ast_analysis'] = {
                'integration_candidates': [
                    ic.to_dict() for ic in self.integration_candidates
                ]
            }

        return result

    def categorize_integrations(self, project_types: set[str]) -> dict[str, list[dict[str, Any]]]:
        """
        Categorize integration candidates into interunit/extlib/boundaries/unknown.

        Args:
            project_types: set of FQNs from project inventory

        Returns:
            dict mapping category string to a list of IntegrationFact dicts
        """
        categorized: dict[IntegrationCategory, list[dict[str, Any]]] = {
            IntegrationCategory.INTERUNIT: [],
            IntegrationCategory.EXTLIB: [],
            IntegrationCategory.BOUNDARY: [],
            IntegrationCategory.UNKNOWN: []
        }

        for candidate in self.integration_candidates:
            category = self._determine_category(candidate.target, project_types)
            fact = candidate.to_ledger_integration_fact()
            categorized[category].append(fact)

        # Remove empty categories and convert enum keys to strings
        return {
            cat.value: facts
            for cat, facts in categorized.items()
            if facts
        }

    def _determine_category(self, target: str, project_types: set[str]) -> IntegrationCategory:
        """Determine integration category."""
        # Check if the target is in the project
        if target in project_types:
            return IntegrationCategory.INTERUNIT

        # Check for boundary indicators (operations that cross system boundaries)
        boundary_indicators: list[str] = [
            'open', 'requests.', 'urllib.', 'http.client.',
            'os.getenv', 'os.environ',
            'datetime.now', 'time.time', 'time.sleep',
            'random.', 'subprocess.',
            'socket.', 'http.',
        ]
        if any(indicator in target for indicator in boundary_indicators):
            return IntegrationCategory.BOUNDARY

        # Check for stdlib patterns (heuristic)
        stdlib_patterns: list[str] = [
            'json.', 'os.', 'sys.', 're.', 'math.',
            'collections.', 'itertools.', 'functools.',
            'pathlib.', 'typing.', 'dataclasses.',
            'Path', 'Path.', 'Path(',  # pathlib.Path
        ]
        if any(pattern in target for pattern in stdlib_patterns):
            return IntegrationCategory.EXTLIB

        # Common third-party libraries that should be extlib
        extlib_packages: list[str] = [
            'tomli.', 'tomli_w.',  # TOML libraries
            'yaml.', 'pyyaml.',  # YAML libraries
            'lxml.', 'bs4.',  # XML/HTML parsing
            'numpy.', 'pandas.',  # Data science
            'pytest.', 'unittest.',  # Testing
        ]
        if any(pkg in target for pkg in extlib_packages):
            return IntegrationCategory.EXTLIB

        # Cannot determine - mark as unknown
        return IntegrationCategory.UNKNOWN

    def to_ledger_callable_spec(self, project_types: set[str]) -> dict[str, Any]:
        """
        Transform to ledger CallableSpec format.

        Args:
            project_types: set of FQNs for categorizing integrations

        Returns:
            dict in ledger CallableSpec format
        """
        spec: dict[str, Any] = {
            'branches': [b.to_ledger_ei_spec() for b in self.branches]
        }

        if self.params:
            spec['params'] = [p.to_dict() for p in self.params]

        if self.return_type:
            spec['returnType'] = self.return_type.to_dict()

        # Add categorized integrations
        integration = self.categorize_integrations(project_types)
        if integration:
            spec['integration'] = integration

        return spec


# =============================================================================
# Helper Functions
# =============================================================================

def validate_ei_id(ei_id: str) -> bool:
    """
    Validate the EI ID format.

    Valid formats:
        C000F001E0001 (unit function)
        C001M002E0003 (class method)
        C001M002N001E0004 (nested function)
    """
    import re
    pattern = r'^C\d{3}(?:_[A-Z]\d{3})*E\d{4}$'
    return bool(re.match(pattern, ei_id))


def validate_integration_id(integration_id: str) -> bool:
    """
    Validate the integration ID format.

    Must be 'I' + valid EI ID.
    """
    if not integration_id.startswith('I'):
        return False
    return validate_ei_id(integration_id[1:])