"""
Core data structures for integration flow generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TargetRef:
    """Reference to a resolved integration target."""
    status: str  # resolved | ambiguous | unresolved
    unit_id: str | None = None
    callable_id: str | None = None
    name: str | None = None
    raw: str | None = None
    note: str | None = None


@dataclass
class BoundarySummary:
    """Summary of boundary integration details."""
    kind: str  # filesystem | database | network | subprocess | etc.
    protocol: str | None = None
    system: str | None = None
    endpoint: str | None = None
    operation: str | None = None
    resource: str | None = None


@dataclass
class IntegrationPoint:
    """
    A single integration point (seam) extracted from a unit ledger.

    This represents one integration fact (either interunit or boundary)
    with its full context preserved.
    """
    id: str  # Integration ID (e.g., IC000F001E0004)
    source_unit: str
    source_callable_id: str
    source_callable_name: str
    target_raw: str
    target_resolved: TargetRef | None
    kind: str  # call | construct | import | dispatch | io | other
    execution_paths: list[list[str]]  # List of EI ID sequences
    condition: str | None = None
    boundary: BoundarySummary | None = None
    signature: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            'id': self.id,
            'sourceUnit': self.source_unit,
            'sourceCallableId': self.source_callable_id,
            'sourceCallableName': self.source_callable_name,
            'target': self.target_raw,
            'kind': self.kind,
            'executionPaths': self.execution_paths,
        }

        if self.target_resolved:
            result['targetResolved'] = {
                'status': self.target_resolved.status,
                'unitId': self.target_resolved.unit_id,
                'callableId': self.target_resolved.callable_id,
                'name': self.target_resolved.name,
            }

        if self.condition:
            result['condition'] = self.condition

        if self.boundary:
            result['boundary'] = {
                'kind': self.boundary.kind,
                'protocol': self.boundary.protocol,
                'system': self.boundary.system,
                'endpoint': self.boundary.endpoint,
                'operation': self.boundary.operation,
                'resource': self.boundary.resource,
            }

        if self.signature:
            result['signature'] = self.signature

        if self.notes:
            result['notes'] = self.notes

        return result


@dataclass
class IntegrationPointClassification:
    """Classification of integration points by their role in flows."""
    entry_points: list[str] = field(default_factory=list)  # Integration IDs
    intermediate_seams: list[str] = field(default_factory=list)
    terminal_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'stage': 'integration-point-classification',
            'entryPoints': self.entry_points,
            'intermediateSeams': self.intermediate_seams,
            'terminalNodes': self.terminal_nodes,
            'metadata': {
                'entryPointCount': len(self.entry_points),
                'intermediateCount': len(self.intermediate_seams),
                'terminalNodeCount': len(self.terminal_nodes),
            }
        }


@dataclass
class IntegrationEdge:
    """Edge in the integration graph."""
    from_id: str  # Integration point ID
    to_id: str  # Integration point ID
    reason: str  # Why this edge exists


@dataclass
class IntegrationGraph:
    """Graph of integration points and their relationships."""
    nodes: list[IntegrationPoint] = field(default_factory=list)
    edges: list[IntegrationEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'stage': 'integration-graph',
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [
                {
                    'from': edge.from_id,
                    'to': edge.to_id,
                    'reason': edge.reason,
                }
                for edge in self.edges
            ],
            'metadata': {
                'nodeCount': len(self.nodes),
                'edgeCount': len(self.edges),
            }
        }


@dataclass
class EntryPointInfo:
    """Information about flow entry point."""
    unit_id: str
    callable_id: str
    callable_name: str
    way_in: str  # How to invoke this entry point


@dataclass
class TerminalNodeInfo:
    """Information about flow terminal node."""
    integration_id: str
    boundary: str | None = None  # Boundary kind if applicable


@dataclass
class Flow:
    """
    A complete flow from entry point to terminal node.

    Represents a sequence of integration points that execution
    can traverse through the system.
    """
    id: str  # Flow ID (e.g., FLOW_001)
    length: int
    sequence: list[IntegrationPoint]
    entry_point: EntryPointInfo
    terminal_node: TerminalNodeInfo
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'flowId': self.id,
            'description': self.description,
            'length': self.length,
            'sequence': [point.to_dict() for point in self.sequence],
            'entryPoint': {
                'unitId': self.entry_point.unit_id,
                'callableId': self.entry_point.callable_id,
                'callableName': self.entry_point.callable_name,
                'wayIn': self.entry_point.way_in,
            },
            'terminalNode': {
                'integrationId': self.terminal_node.integration_id,
                'boundary': self.terminal_node.boundary,
            }
        }


@dataclass
class Window:
    """
    A sliding window of a flow representing a potential test scope.

    Windows are subsets of complete flows that define what to test
    together (system under test) and what to mock.
    """
    id: str  # Window ID (e.g., FLOW_001_W2_001)
    parent_flow_id: str
    length: int
    sequence: list[IntegrationPoint]
    system_under_test: list[str]  # Unit names
    mock_boundary: str  # What to mock
    entry_point: str  # How to invoke this test
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'windowId': self.id,
            'parentFlowId': self.parent_flow_id,
            'description': self.description,
            'length': self.length,
            'sequence': [point.to_dict() for point in self.sequence],
            'systemUnderTest': self.system_under_test,
            'mockBoundary': self.mock_boundary,
            'entryPoint': self.entry_point,
        }
