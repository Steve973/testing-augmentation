# Unit Ledger System

**Systematic 100% test coverage through exhaustive execution item enumeration.**

The Unit Ledger system provides a language-agnostic, procedural methodology for achieving complete branch coverage in software testing. Instead of hoping tests cover everything, the ledger creates a deterministic inventory of all execution paths, enabling AI and human testers to generate comprehensive test suites mechanically.

---

## What is a Unit Ledger?

A **Unit Ledger** is a complete inventory of all execution items (EIs) in a code unit. Each EI represents a distinct outcome path that can occur when executing a single line of code.

Think of it as:
- **For testing**: A checklist ensuring every code path has been tested
- **For AI**: A structured specification that enables deterministic test generation
- **For requirements**: A traceability map from requirements → code → tests
- **For porting**: Preservation of test coverage across language migrations

## The Problem

Traditional testing approaches rely on:
- **Intuition**: "I think I've covered the important cases"
- **Coverage tools**: "87% coverage - is that enough?"
- **AI guessing**: "Generate tests for this code" → inconsistent results

**Result:** Missed edge cases, incomplete coverage, unpredictable quality.

## The Solution

The Unit Ledger system makes test coverage:
- **Enumerable**: Every execution path gets a unique ID
- **Verifiable**: Coverage becomes a checklist of EI IDs
- **Deterministic**: Same code → same ledger → same coverage
- **AI-compatible**: A structured format enables reliable AI test generation

---

## Quick Start

### 1. Generate a Ledger

Read the [Unit Ledger Generation Procedure](unit-ledger-spec.md) and generate a ledger for your code unit:

```python
# Input: Your source code
def classify_value(x: int) -> str:
    if x < 0:
        return "negative"
    if x == 0:
        return "zero"
    return "positive"
```

```yaml
# Output: Three-document YAML ledger
docKind: derived-ids
# ... Document 1: All IDs assigned ...
---
docKind: ledger
# ... Document 2: Complete EI inventory ...
---
docKind: ledger-generation-review
# ... Document 3: Generation findings ...
```

### 2. Generate Tests

Read the [Unit Testing Contract](unit-testing-contract.md) and generate tests from your ledger:

```python
@pytest.mark.parametrize("x,expected,covers", [
    (-5, "negative", ["C000F001E0001"]),
    (0, "zero", ["C000F001E0002", "C000F001E0003"]),
    (10, "positive", ["C000F001E0002", "C000F001E0004", "C000F001E0005"]),
])
def test_classify_value(x, expected, covers):
    # covers: see parameter
    assert classify_value(x) == expected
```

### 3. Verify Coverage

Run your tests with a coverage tool and confirm 100% of enumerated EIs are exercised.

---

## Repository Contents

### Core Specifications

- **[unit-ledger-spec.md](unit-ledger-spec.md)**
  - The complete Unit Ledger Generation Procedure
  - Language-agnostic methodology
  - 5-stage procedural generation
  - Definitions, examples, verification gates
  - JSON schema for validation

- **[unit-testing-contract.md](unit-testing-contract.md)**
  - Rules and workflow for generating tests from ledgers
  - 7-stage deterministic test generation
  - Mocking and isolation requirements
  - Blocked EI protocol (no-stall testing)
  - Complete worked examples

- **[unit-ledger-spec_schema.json](unit-ledger-spec.schema.json)**
  - JSON schema for validating generated ledgers
  - Strict validation rules
  - ID format patterns
  - Required/optional field definitions

### Prompts and Tools

- **[ledger-generation-prompt.md](prompt.md)**
  - Instructions for AI systems generating ledgers
  - Optimized for Claude and GPT
  - Prevents common AI errors
  - Enforces procedural execution

### Language Companion Guides

- **[language-companion-guides/](./unit/language-companion-guides/)**
  - Language-specific pattern libraries
  - **[README.md](language-companion-guides/README.md)**
    - Guide to creating and using companions
  - **[companion-guide-template.md](language-companion-guides/unit-ledger-language-companion-template.md)**
    - Template for new guides
  - **[python-unit-ledger-companion.md](language-companion-guides/python-unit-ledger-companion.md)**
    - Python examples (when available)
  - **[java-unit-ledger-companion.md](language-companion-guides/java-unit-ledger-companion.md)**
    - Java examples (when available)
  - More languages are welcome via community contributions!

---

## Key Concepts

### Execution Item (EI)

An atomic unit of execution - a distinct outcome path for a single line of code.

```python
# This line has 2 EIs:
if x > 0:
    # EI-1: condition true → enter block
    # EI-2: condition false → skip block

# This line has 3 EIs:
items = [x for x in data if x.valid]
  # EI-1: data empty → items = []
  # EI-2: data not empty, all filtered → items = []
  # EI-3: data not empty, some pass → items populated
```

### Integration Facts

Details about how a unit interacts with code outside its boundaries:
- **Interunit**: Calls to other project units
- **Boundary**: Calls crossing external system boundaries (network, filesystem, database)
- **Execution Paths**: EI sequences needed to reach each integration point

Integration facts tell you **what to mock** and **how to reach it** in your tests.

### Deterministic Generation

The ledger generation procedure is **mechanical, not interpretive**:
- Same input code → same ledger output
- No guessing or creative interpretation
- Strictly follows enumeration rules
- Verifiable at each stage via gates

This determinism enables:
- Reliable AI-assisted generation
- Consistent human-generated ledgers  
- Automated validation
- Reproducible results

---

## Why This Works

### For Humans

- **No guessing**: The procedure tells you exactly what to enumerate
- **Systematic**: Work through code line-by-line, miss nothing
- **Verifiable**: Schema validation confirms correctness
- **Traceable**: EI IDs link code → tests → requirements

### For AI Systems

- **Structured**: YAML format is machine-parseable
- **Procedural**: Clear step-by-step instructions prevent hallucination
- **Validatable**: Schema catches errors automatically
- **Deterministic**: Repeatable results, not creative interpretation

### For Teams

- **Language-agnostic**: Works for Python, Java, Kotlin, Rust, Go, etc.
- **Portable**: Preserve test coverage when porting between languages
- **Reviewable**: Ledgers make coverage gaps visible in code review
- **Scalable**: Same process for small functions and large modules

---

## Use Cases

### 1. Unit Testing with AI

**Problem:** "AI, generate tests for this code" produces inconsistent, incomplete results.

**Solution:** 
1. Generate ledger (enumeration of all EIs)
2. Point AI at ledger + testing contract
3. AI generates tests systematically, covering all EI IDs
4. Verify 100% coverage

### 2. Cross-Language Porting

**Problem:** Porting code from Python to Java loses test coverage.

**Solution:**
1. Generate ledger from Python source
2. Port Python code to Java
3. Generate Java tests using same ledger
4. Coverage preserved across languages

### 3. Requirement Traceability

**Problem:** Hard to prove every requirement is tested.

**Solution:**
1. Map requirements to EI IDs in ledger
2. Map tests to EI IDs they cover
3. Traceable chain: Requirement → EI ID → Test

### 4. Legacy Code Coverage

**Problem:** Legacy code has no tests, coverage is daunting.

**Solution:**
1. Generate ledger for legacy unit
2. See complete inventory of what needs testing
3. Generate tests incrementally, tracking progress
4. No guessing about what's left

### 5. Integration Test Planning

**Problem:** Don't know where systems integrate or what needs mocking.

**Solution:**
1. Generate ledgers for all units
2. Extract integration facts (boundaries, interunit calls)
3. Map integration flows across units
4. Systematic integration test planning

---

## Workflow Example

### Step 1: Generate Ledger

```bash
# Using AI assistant with ledger-generation-prompt.md
$ claude-chat --file unit.py --prompt ledger-generation-prompt.md

# Output: unit-ledger.yaml (three documents)
```

### Step 2: Validate Ledger

```bash
# Validate against schema
$ jsonschema -i unit-ledger.yaml unit-ledger-spec_schema.json
✓ Validation passed
```

### Step 3: Generate Tests

```bash
# Using AI assistant with unit-testing-contract.md
$ claude-chat --file unit.py --file unit-ledger.yaml --prompt "Generate unit tests following the testing contract"

# Output: test_unit.py
```

### Step 4: Verify Coverage

```bash
# Run tests with coverage
$ pytest --cov=unit --cov-report=term-missing test_unit.py

unit.py                    100%
```

### Step 5: Commit

```bash
$ git add unit.py test_unit.py unit-ledger.yaml
$ git commit -m "Add unit with 100% coverage via ledger"
```

---

## Design Philosophy

### Procedural Over Interpretive

The system is **deterministic by design**. Instead of asking "be thorough," we
specify exactly what to enumerate and how to enumerate it. This removes ambiguity
and produces consistent results.

### Observation Over Inference

Ledgers capture **what's literally present** in the code, not interpretations or
assumptions. This makes them objective, verifiable, and language-agnostic.

### Progress Over Perfection

The blocked EI protocol ensures uncertainty doesn't stall progress. If something
can't be tested without missing information, mark it blocked and continue. No paralysis.

### Mechanical Over Creative

Test generation follows a deterministic 7-stage procedure. No searching for "optimal"
layouts, no creative interpretation. Just execute the stages in order.

---

## Contributing

We welcome contributions in several areas:

### 1. Language Companion Guides

Create examples for your language following the
[companion guide template](language-companion-guides/unit-ledger-language-companion-template.md).

**Needed languages:** JavaScript, TypeScript, Go, Rust, C++, C#, Ruby, PHP, Swift, Kotlin

### 2. Tooling

Build tools to automate ledger generation and validation:
- Static analysis parsers
- IDE plugins
- CI/CD integrations
- Coverage visualization

### 3. Examples

Add real-world examples demonstrating the system:
- Complex codebases
- Different languages
- Integration testing
- Cross-language ports

### 4. Documentation

Improve clarity, add diagrams, create tutorials, fix typos.

**How to contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

---

## FAQ

### Q: Is this just branch coverage?

**A:** Yes and no. Traditional "branch coverage" focuses on conditional
statements. The Unit Ledger enumerates **all execution items**, including
conditionals, loops, exceptions, sequential statements. We call them EIs for
precision, but coverage tools report them as branches.

### Q: Do I need to use AI?

**A:** No. The ledger and testing contract are human-readable procedures. AI
can accelerate the process, but humans can follow the same steps manually.

### Q: What languages are supported?

**A:** All languages. The core procedure is language-agnostic. Language
companion guides provide language-specific examples, but the principles work
universally.

### Q: How long does this take?

**A:** With AI assistance:
- Small unit (5–10 functions): 1 minute
- Medium unit (20–30 functions): 2 minutes
- Large unit (50+ functions): 5–10 minutes

Manual generation takes longer but is still systematic.

### Q: Can I use this with existing tests?

**A:** Yes. Generate the ledger, then verify existing tests cover all EI IDs.
Add tests for missing coverage.

### Q: Does this work for integration tests?

**A:** The ledger is designed for unit testing. However, integration facts in
the ledger inform integration test planning by identifying all boundary
crossings and interunit calls.

### Q: What about mutation testing?

**A:** The Unit Ledger ensures every path is executed. Mutation testing ensures
every path is **correctly** tested. They're complementary, so use both.

---

## License

[Specify your license - MIT, Apache 2.0, etc.]

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/unit-ledger/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/unit-ledger/discussions)
- **Email**: your.email@example.com

---

## Acknowledgments

This system emerged from observing that AI systems (and humans) make consistent
errors when asked to "be thorough" without specific procedures. By making
enumeration mechanical rather than interpretive, we achieve deterministic,
repeatable results.

Special thanks to early adopters who tested the methodology and provided feedback.

---

**Ready to achieve 100% coverage?** Start with the
[Unit Ledger Generation Procedure](unit-ledger-spec.md).