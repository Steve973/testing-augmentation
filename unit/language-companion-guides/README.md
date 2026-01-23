# Language Companion Guides

## What Are Language Companion Guides?

Language companion guides are language-specific reference documents that show
exactly how to apply the Unit Ledger Generation Procedure to code in a
particular programming language (Python, Java, Kotlin, Rust, etc.).

The core Unit Ledger specification is **language-agnostic** - it describes the
principles and procedures that work for any language. Companion guides make
those principles **concrete** by showing language-specific examples for every
construct pattern.

## Why Do We Need Them?

While the core procedure is universal, each programming language has its own:
- **Syntax patterns** (ternary operators, list comprehensions, pattern matching)
- **Control flow constructs** (if/elif/else vs. switch/case vs. match)
- **Collection operations** (list comprehensions vs. streams vs. iterators)
- **Exception handling** (try/catch, try/except, finally blocks, resource mgmt.)
- **Language-specific idioms** (null safety operators, async/await, decorators)

A companion guide bridges the gap between "here's the universal procedure" and
"here's exactly what an `if/else` in Python looks like when you run it through
the procedure."

## What Value Do They Provide?

### For Humans Using AI to Generate Ledgers
When you ask an AI to generate a unit ledger for your Python/Java/Kotlin code,
you can:
1. Point it at the core spec (universal principles)
2. Point it at the companion guide for your language (concrete examples)
3. Get accurate, consistent results

The guide shows the AI **exactly** what patterns to look for and how to
enumerate them.

### For Humans Creating Ledgers Manually
Companion guides serve as:
- **Quick reference** – "How many EIs does a for loop create? Check section 2.3.1"
- **Pattern library** – "Here's what a try/except with multiple handlers looks like"
- **Validation tool** – "Does my outcome map match the example?"

### For the Community
- **Shared understanding** – Everyone using Python sees the same examples
- **Quality control** – Contributions can be verified against the guide
- **Onboarding** – New contributors learn by example

## How to Use a Companion Guide

### When Generating a Ledger

**Step 1:** Read the core Unit Ledger Generation Procedure spec

**Step 2:** Open the companion guide for your language

**Step 3:** For each construct in your code:
- Find the matching section in the companion guide
- Review the 4-part example:
  - Source code (does this match your construct?)
  - Outcome path analysis (what outcomes exist?)
  - EI ID assignment (how many EIs?)
  - YAML representation (what does the output look like?)

**Step 4:** Apply the same pattern to your code

**Example:** You encounter this Python code:
```python
if user.is_active:
    send_notification(user)
```

Look up section 2.2.2 "If Without Else" in the Python companion guide. You'll
see:
- Source code example
- Outcome map showing two outcomes (condition true, condition false)
- EI ID assignment (2 EIs)
- YAML showing how to represent it

### When Contributing to a Guide

See "How to Create a Companion Guide" below.

## How to Create a Companion Guide

Creating a companion guide is straightforward - you're not writing prose, you're
creating **worked examples**.

### The Template Structure

Every companion guide follows the same structure
(see `companion-guide-template.md`):

1. **Language Overview** (brief context about the language)
2. **EI Enumeration Patterns** (constructs organized by category)
3. **Integration Facts Patterns** (how to identify integration points)
4. **Language-Specific Gotchas** (edge cases and subtleties)
5. **Complete Examples** (5–10 full worked examples)
6. **Quick Reference Tables** (fast lookup)

### The 4-Part Pattern

For each construct pattern (if/else, for loop, try/catch, etc.), you provide:

```markdown
#### 2.2.1 If/Else Statements

##### 2.2.1.1 Source Code
[Small, clear code example showing this pattern]

##### 2.2.1.2 Outcome Path Analysis (Stage 1 Output)
[The outcome map produced by Stage 1 of the procedure]

##### 2.2.1.3 EI ID Assignment (Stage 2 Output)
[The EI mappings produced by Stage 2 of the procedure]

##### 2.2.1.4 YAML Representation (Stage 4 Output - Document 2 excerpt)
[The relevant YAML from Document 2 showing how this appears in the ledger]
```

### Step-by-Step Guide Creation Process

**1. Choose Your Language**
Pick a language you know well (Python, Java, Kotlin, Rust, etc.)

**2. Copy the Template**
Start from `companion-guide-template.md`

**3. Fill in Section 1 (Language Overview)**
Brief description:
- Language type (compiled/interpreted)
- Control flow constructs that are available
- Unique features that affect EI enumeration

**4. Work Through Section 2 (EI Patterns)**
For each subsection (2.1, 2.2, 2.3, etc.):
- Write a small code example (5–10 lines max)
- Run it through the procedure (manually or with AI)
- Capture the Stage 1 outcome map
- Capture the Stage 2 EI assignments
- Capture the relevant Stage 4 YAML
- Fill in the four subsection slots

**5. Work Through Section 3 (Integration Patterns)**
Same process, but focus on:
- Method calls
- Standard library boundaries (file I/O, network, database)
- Framework-specific patterns

**6. Document Gotchas (Section 4)**
Note any language-specific edge cases:
- Implicit execution (property getters, operator overloading)
- Multi-line expressions
- Short-circuit evaluation
- Type system quirks

**7. Create Complete Examples (Section 5)**
5-10 full worked examples showing:
- Real-world patterns
- Multiple stages together
- Integration facts
- Complete YAML output

**8. Build Quick Reference Tables (Section 6)**
Create lookup tables:
- Construct → EI count
- Standard library → boundary kind
- Pattern → integration kind

### Tips for Quality

**Keep examples minimal:**
- Each example demonstrates ONE pattern
- Remove extraneous code
- Use simple, clear variable names

**Be mechanically precise:**
- Run examples through the actual procedure
- Don't guess at EI counts
- Validate YAML against the schema

**Cover the common cases:**
- Focus on patterns developers use daily
- Include language idioms
- Don't chase obscure edge cases initially

**Make it scannable:**
- Use consistent formatting
- Keep subsections parallel in structure
- Use tables for quick lookup

## Contributing Your Guide

Once you've created a companion guide:

1. **Test it** – Use it to generate a few ledgers and verify accuracy
2. **Submit a PR** – Add your guide to the repository
3. **Respond to feedback** – Community review helps improve quality
4. **Iterate** – Guides can start minimal and grow over time

## Repository Structure

```
language-companion-guides/
├── README.md                      # This file
├── companion-guide-template.md    # Template to copy
├── python.md                      # Python companion guide
├── java.md                        # Java companion guide
├── kotlin.md                      # Kotlin companion guide
└── ...                            # More languages welcome!
```

## Getting Started

**To use a guide:**
1. Find the guide for your language in `guides/`
2. Read alongside the core Unit Ledger spec
3. Look up patterns as you encounter them in your code

**To create a guide:**
1. Copy `companion-guide-template.md`
2. Fill in the sections for your language
3. Test it on real code
4. Submit a PR

## Philosophy

**Companion guides are specimens, not prose.**

The goal is to show, not tell. Each section is a worked example that
demonstrates the procedure in action. Contributors are not just writing
documentation. They are creating reference examples that others can
pattern-match against.

The mechanical nature of the procedure means guides can be:
- Created systematically (work through the template)
- Verified objectively (does the output match the schema?)
- Used reliably (same input → same output)

## Community Contributions Welcome

Every language guide makes the Unit Ledger system more useful. If you work in a
language that doesn't have a guide yet:
- **Create one!** Copy the template and start filling it in
- **Start small** – A minimal guide is better than no guide
- **Iterate** – Guides can grow and improve over time
- **Share** – Others will benefit from your work

---

**Questions?** Open an issue or discussion in the repository. We're here to help!
