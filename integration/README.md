# Integration Flow Testing (Work in Progress)

## Status: Design Phase

This directory will contain the specification and procedures for integration flow testing. This README captures the initial design thinking and approach.

---

## Core Concept

**Integration flow testing focuses on SEAMS, not internal execution paths.**

- **Unit tests** verify all execution items (EIs) within a single unit - exhaustive internal path coverage
- **Integration tests** verify how units compose across their boundaries - seam interaction coverage

Integration flows are sequences of integration points (seams) across multiple units. We test these flows with use case coverage: happy paths, boundary conditions, and error conditions.

---

## The Graph Model

### Nodes: Integration Points

Every integration fact from unit ledgers becomes a node:
- **Interunit integrations:** Calls from Unit A to Unit B
- **Boundary integrations:** Calls to external systems (network, filesystem, database, etc.)

Example nodes:
- `IC000F001E0004` - Unit A calls Unit B.process_data()
- `IC001F002E0007` - Unit B calls Unit C.fetch()
- `IC002F001E0012` - Unit C calls requests.get() [boundary]

### Edges: Integration Dependencies

An edge exists when one integration can lead to another:
- If integration I1 can cause integration I2 to execute, create edge I1 → I2
- Determined by: Call relationships and execution paths in the code

### Flows: Sequences of Seams

A flow is a path through the graph from entry point to terminal node:
- **Entry points:** First seam in a flow (public API, event handler, message consumer)
- **Terminal nodes:** Boundaries (external system calls) or natural conclusions
- **Flow:** Sequence of integration IDs representing how units compose

Example flow:
```
Entry: A.handle_request
  ↓ (seam: A→B)
B.process_data
  ↓ (seam: B→C)
C.fetch
  ↓ (seam: C→API)
requests.get [boundary]

Flow: [IC000F001E0004 → IC001F002E0007 → IC002F001E0012]
Meaning: "A calls B, which calls C, which calls external API"
```

---

## The Sliding Window Approach

### Complete Flow Enumeration

1. Build the integration graph from all unit ledgers in scope
2. Identify all complete flows (entry point → terminal node)
3. For each flow of length N, generate all sliding windows of length 2 to N

### Sliding Windows

For a flow `[A→B, B→C, C→API]` (length 3):

**Windows of length 2:**
- `[A→B, B→C]` - Test A and B integration, mock C
- `[B→C, C→API]` - Test B and C integration, mock API

**Windows of length 3:**
- `[A→B, B→C, C→API]` - Test full flow, mock only API

Each window represents a potential integration test with different scope.

### Why Sliding Windows?

Different window lengths test different composition depths:
- **Smaller windows (2-3 seams):** More focused, easier to debug, faster tests
- **Larger windows (4+ seams):** More comprehensive, closer to real system behavior
- **All windows:** Ensure every seam pair is tested together

---

## Test Scope and Mocking Strategy

### Test Scope = Units in the Window

For window `[A→B, B→C]`:
- **System under test:** Units A and B (real, unmocked)
- **Mock boundary:** Unit C's interface
- **Entry point:** Call A's public API (the "way in")

For window `[A→B, B→C, C→API]`:
- **System under test:** Units A, B, and C (real, unmocked)
- **Mock boundary:** External API
- **Entry point:** Call A's public API (the "way in")

### The "Way In"

To test an integration flow, you need an entry point:
- The first seam's caller (often a public API, endpoint, or event handler)
- Use minimal execution paths to reach the first seam
- Don't test all internal EI variations (that's what unit tests do)

Example:
```python
def test_integration_flow_a_to_c(mock_api):
    # Entry point: Call A's public interface
    # Use simple, valid input (minimal path to seams)
    result = A.handle_request({"user_id": "123"})
    
    # Assert on SEAM behavior:
    # - Did the flow complete correctly?
    # - Was the API called as expected?
    # - Did data flow through A→B→C correctly?
    assert result == expected_output
    mock_api.get.assert_called_once_with("/users/123")
```

---

## Use Case Coverage for Seams

For each integration flow window, test with use case coverage:

### Happy Paths
- Normal data flows through the seam chain correctly
- Success responses propagate back properly
- State changes happen as expected across boundaries

### Boundary Conditions
- Empty collections at seam boundaries
- Null/None values crossing seams
- Maximum/minimum values that test contract limits
- Edge cases in data transformation between units
- Large datasets flowing through seams

### Error Conditions
- Exceptions raised at seams - do they propagate correctly?
- Timeouts at external boundaries
- Invalid data shapes crossing seams (contract violations)
- Partial failures in multi-step flows

### Example Use Case Matrix

For flow window `[A→B, B→C, C→API]`:

| Use Case | Entry Input | Mock Behavior | Expected Outcome | Category |
|----------|-------------|---------------|------------------|----------|
| Normal success | `{"user_id": "123"}` | API returns `{"status": "ok"}` | Data flows correctly, result returned | Happy path |
| Empty API response | `{"user_id": "123"}` | API returns `{}` | System handles gracefully | Boundary |
| API timeout | `{"user_id": "123"}` | API raises Timeout | Error propagates to A | Error |
| Invalid data from B | `{"user_id": "123"}` | B returns wrong type | Contract violation caught | Error |
| Large dataset | `{"user_id": "123"}` | API returns 10k items | Handles large data | Boundary |

---

## What We're NOT Testing

Integration tests focus on seams, not internal logic:

**NOT tested in integration tests:**
- All EI variations within each unit (unit tests cover this)
- Every possible input combination (unit tests cover this)
- Internal branching and conditionals (unit tests cover this)

**Tested in integration tests:**
- Do units call each other correctly at boundaries?
- Do data contracts match at seams?
- Do errors propagate correctly across seams?
- Does the composition work end-to-end?

### Example Contrast

**Unit test (exhaustive EI coverage):**
```python
def test_handle_request_empty_input():
    # covers: C000F001E0001
    with pytest.raises(ValueError):
        A.handle_request(None)

def test_handle_request_high_priority():
    # covers: C000F001E0004
    result = A.handle_request({"priority": "high", "value": "x"})
    # ... detailed assertions on A's internal behavior

def test_handle_request_normal_priority():
    # covers: C000F001E0005
    result = A.handle_request({"value": "x"})
    # ... detailed assertions on A's internal behavior
```

**Integration test (minimal paths, focus on seams):**
```python
def test_a_to_b_to_c_happy_path(mock_api):
    # Use ONE simple valid path to reach the seams
    # Don't test all input variations - that's what unit tests do
    mock_api.get.return_value = {"data": "success"}
    
    result = A.handle_request({"user_id": "123"})
    
    # Assert on SEAM behavior, not internal EI behavior:
    assert result == {"data": "success"}
    mock_api.get.assert_called_once()

def test_a_to_b_to_c_api_error(mock_api):
    # Test error propagation ACROSS seams
    mock_api.get.side_effect = ConnectionError("API down")
    
    with pytest.raises(ServiceUnavailableError):
        A.handle_request({"user_id": "123"})
```

---

## Window Filtering (Future Work)

Not all sliding windows may be worth testing. Future work will define filtering criteria:

### Potentially Keep (High Value)
- Windows ending at boundaries (test system interaction with external world)
- Windows spanning multiple units (test inter-unit contracts)
- Windows with error propagation (often missed in unit tests)
- Windows representing critical business flows

### Potentially Discard (Lower Value or Redundant)
- Windows fully covered by smaller windows (if composition doesn't add risk)
- Pure pass-through windows (unit just forwards data unchanged)
- Internal chaining within same unit (unit tests likely cover adequately)

**Decision:** Start by generating all windows, collect data on usefulness, then determine filtering criteria based on real-world experience.

---

## Future Integration Flow Specification

The complete specification will include:

### Stage 1: Build Integration Graph
- Collect all integration facts from unit ledgers
- Create nodes for each integration ID
- Create edges based on call relationships
- Identify entry points and terminal nodes

### Stage 2: Enumerate Complete Flows
- Find all paths from entry points to terminal nodes
- Record full flow sequences (length N)

### Stage 3: Generate Sliding Windows
- For each complete flow of length N:
  - Generate all subflows of length 2
  - Generate all subflows of length 3
  - ...
  - Generate all subflows of length N

### Stage 4: Filter Test-Worthy Windows (TBD)
- Apply filtering criteria (to be determined)
- Determine which windows represent meaningful tests
- Mark redundant windows

### Stage 5: Generate Integration Test Specifications
- For each test-worthy window:
  - Identify system under test (which units are real)
  - Determine mock boundaries
  - Identify entry point ("way in")
  - Generate use case matrix (happy, boundary, error)
  - Specify assertions for each use case

### Stage 6: Generate Integration Tests
- Similar to unit test generation contract
- But focused on seam interactions, not EI exhaustiveness
- Use case coverage for each window

### Stage 7: Validation
- Verify all critical flows are tested
- Verify no duplicate coverage (if filtering applied)
- Confirm mock boundaries are correct

---

## Open Questions

These will be resolved during specification development:

1. **Graph construction precision:** Are edges between specific integration IDs, or between callables more broadly?

2. **Entry point detection:** What makes an integration point an "entry"? Do we need ledger annotations?

3. **Edge determination:** How do we mechanically determine if integration I1 can lead to I2? Do we need path analysis across units?

4. **Window filtering strategy:** Generate all windows (comprehensive), or filter to valuable subset (targeted)?

5. **Test oracle definition:** For a given window, what exactly are we asserting? Flow completion? Data correctness? Side effects?

6. **Mock scope flexibility:** Can we mock in the middle of a window, or only at window boundaries?

---

## Relationship to Unit Testing

Integration flow testing complements unit testing:

| Aspect | Unit Testing | Integration Flow Testing |
|--------|--------------|--------------------------|
| **Focus** | Execution items within one unit | Seams between units |
| **Coverage** | 100% of EIs (exhaustive paths) | Use case coverage of seam interactions |
| **Scope** | Single unit, mock everything outside | Multiple units, mock at window boundary |
| **Failures mean** | Internal logic is wrong | Units don't compose correctly |
| **Generated from** | Unit Ledger (EI enumeration) | Integration Flow Graph (seam enumeration) |
| **Execution paths** | Test all variations | Use minimal valid paths to reach seams |

**Together they provide:**
- Unit tests: Every line of code works correctly in isolation
- Integration tests: Units fit together correctly at their boundaries
- Result: Complete confidence in the system

---

## Next Steps

1. **Validate unit ledger system** with real-world codebases
2. **Build integration graph construction** procedure
3. **Define entry point and terminal node** identification rules
4. **Implement sliding window generation** algorithm
5. **Test on real systems** to determine filtering criteria
6. **Write Integration Flow Generation Procedure** specification
7. **Write Integration Testing Contract** (analogous to Unit Testing Contract)

---

## Contributing

This is an active design area. Contributions welcome:
- Real-world integration testing challenges
- Graph construction approaches
- Window filtering heuristics
- Test generation strategies
- Example integration flows from actual systems

---

**Status:** Conceptual design captured. Implementation pending validation of unit ledger system.