# Testing Augmentation

**Systematic, deterministic test coverage through execution enumeration.**

---

## The Problem

Software testing is typically unsystematic:
- "I think I've covered the important cases" (hope-based testing)
- "87% coverage - good enough?" (arbitrary thresholds)
- "AI, generate tests" → inconsistent, incomplete results

**Result:** Missed edge cases, unpredictable quality, unverifiable completeness.

---

## The Solution

Make test coverage **enumerable** instead of guessable.

**Ledgers** are complete, structured inventories of what needs testing:
- **Unit Ledgers:** Enumerate all execution paths within a code unit
- **Integration Flow Ledgers:** Enumerate all seams between units *(coming soon)*

With a complete inventory:
- Coverage becomes a **checklist** (did we test everything enumerated?)
- Generation becomes **deterministic** (same code → same ledger → same tests)
- Verification becomes **mechanical** (count EI IDs covered vs total)
- AI becomes **reliable** (structured specs prevent hallucination)

---

## How It Works

### 1. Generate the Ledger

Follow a strict procedural specification to enumerate all testable items:

```yaml
# Unit Ledger Output (3 documents)
docKind: derived-ids
# All execution item IDs...
---
docKind: ledger  
# Complete inventory with integration facts...
---
docKind: ledger-generation-review
# Findings and issues...
```

### 2. Generate Tests from the Ledger

Follow a deterministic test generation procedure:

```python
# Tests generated from ledger enumeration
@pytest.mark.parametrize("input,expected,covers", [
    (-5, "negative", ["C000F001E0001"]),
    (0, "zero", ["C000F001E0002", "C000F001E0003"]),
    (10, "positive", ["C000F001E0002", "C000F001E0004", "C000F001E0005"]),
])
def test_classify_value(input, expected, covers):
    assert classify_value(input) == expected
```

### 3. Verify Complete Coverage

Run tests and confirm every enumerated item was exercised:

```bash
$ pytest --cov=unit test_unit.py
unit.py    100%    ✓ All EI IDs covered
```

---

## System Components

### Unit Testing (Available Now)

**[Unit Ledger Generation](./unit/):** Procedural methodology for enumerating all execution items (EIs) within a code unit.
- Language-agnostic 5-stage procedure
- JSON schema validation
- Integration facts for mocking strategy
- AI-optimized prompts

**[Unit Testing Contract](./unit/unit-testing-contract.md):** Rules and workflow for generating tests from unit ledgers.
- Deterministic 7-stage test generation
- 100% EI coverage requirement
- Blocked EI protocol (no-stall testing)
- Mocking and isolation rules

**[Language Companion Guides](./unit/language-companion-guides/):** Language-specific pattern libraries showing how to apply the procedures to Python, Java, etc.

### Integration Testing (Coming Soon)

**Integration Flow Generation:** Graph-based enumeration of seams between units.
- Build integration graph from unit ledgers
- Enumerate complete flows (entry → boundary)
- Generate sliding windows (test scopes of varying size)
- Use case coverage for seam interactions

**Integration Testing Contract:** Rules for testing unit composition.
- Focus on seam interactions, not internal paths
- Use minimal execution paths to reach seams
- Test happy paths, boundary conditions, errors
- Mock at window boundaries

---

## Key Principles

**Enumeration Over Guessing**
- Don't hope you've tested everything - enumerate what needs testing
- Completeness becomes verifiable, not subjective

**Observation Over Inference**
- Capture what's literally present in the code
- Language-agnostic, objective, mechanical

**Procedure Over Interpretation**
- Step-by-step instructions, not creative tasks
- Same input → same output (deterministic)
- Prevents AI hallucination and human inconsistency

**Progress Over Perfection**
- Blocked items don't stall the entire process
- Generate what you can, mark what you can't
- Systematic forward progress

---

## Use Cases

**AI-Assisted Test Generation**
- Point AI at ledger + testing contract
- Get deterministic, complete test coverage
- Verify results mechanically

**Cross-Language Code Porting**
- Generate ledger from Python code
- Port to Java, preserving test coverage
- Generate Java tests from same ledger structure

**Legacy Code Testing**
- Generate ledger for untested code
- See complete inventory of what needs testing
- Generate tests incrementally, track progress

**Requirement Traceability**
- Map requirements → EI IDs → tests
- Prove every requirement is tested
- Track coverage at requirement level

**Integration Test Planning**
- Extract integration facts from unit ledgers
- Map system-wide integration flows
- Generate comprehensive integration test suite

---

## What Makes This Different

**Traditional Approach:**
- Write tests → measure coverage → hope it's enough
- Coverage gaps are invisible until found by bugs
- AI generates tests inconsistently

**This System:**
- Enumerate coverage requirements → generate tests → verify completeness
- Coverage gaps are visible in the ledger
- AI follows strict procedures → deterministic results

**Result:** Testing becomes systematic, verifiable, and complete.

---

## Getting Started

### Start with Unit Testing

1. **Read the [Unit Ledger Specification](./unit/unit-ledger-spec.md)**
2. **Generate a ledger** for your code unit
3. **Validate against schema** (unit-ledger-spec_schema.json)
4. **Generate tests** following the [Unit Testing Contract](./unit/unit-testing-contract.md)
5. **Verify 100% coverage** with your testing framework

### Then Add Integration Testing (Future)

6. **Generate ledgers** for all units in scope
7. **Build integration flow graph** from integration facts
8. **Generate integration tests** for seam composition
9. **Verify complete flow coverage**

---

## Contributing

We welcome contributions:

- **Language companion guides** - Add examples for your language
- **Tooling** - Build automation, IDE plugins, CI/CD integration
- **Examples** - Real-world ledgers and tests
- **Documentation** - Improvements, tutorials, diagrams
- **Integration flow design** - Help design the integration testing system

See individual component READMEs for details.

---

## Status

**Unit Testing System:** Production-ready
- Specification complete
- Schema validation available
- Testing contract defined
- AI prompts optimized
- Language companion guide framework established

**Integration Testing System:** Design phase
- Conceptual approach defined
- Awaiting unit system validation
- Open for design contributions

---

## Philosophy

Testing should be:
- **Systematic** - Follow procedures, not intuition
- **Complete** - Enumerate everything, test everything
- **Verifiable** - Coverage is provable, not estimated
- **Deterministic** - Same code always produces same tests
- **Maintainable** - Changes to code map clearly to test updates

This system makes that possible.

---

## License

This project is licensed under the `MIT License` – see the [LICENSE](LICENSE) file for details.

## Contact

- **Issues:** [GitHub Issues](https://github.com/Steve973/testing-augmentation/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Steve973/testing-augmentation/discussions)

---

**Ready to systematize your testing?** Start with [Unit Testing](./unit/).