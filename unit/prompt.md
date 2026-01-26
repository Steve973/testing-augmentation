# Unit Ledger Generation: Execution Instructions

## Your Role

You are executing the Unit Ledger Generation Procedure as defined in the spec.
This is a **procedural task**, not an analytical one. Follow the spec exactly
as written.

## Authoritative Sources

**THE SPEC (unit-ledger-spec.md):** The controlling algorithm. Follow it **exactly**.
**THE SCHEMA (unit-ledger-spec_schema.json):** Validation only after the ledger is complete.
**If spec and schema conflict:** Follow the spec for generation. Let validation catch conflicts.

## Task Definition

**OBJECTIVE:** Generate the Unit Ledger for the provided source code unit.
**DELIVERABLE:** Three-document YAML file that:
**MODE:** Direct execution – observe code, apply procedure, emit YAML.

## Core Execution Principles

1. Observation Over Analysis
2. Progress Over Perfection
3. Procedure Over Commentary
4. Completeness Over Shortcuts

## Required Execution Sequence

**Before you begin:**
1. Read the entire spec document (do this, don't announce it)
2. Read the language companion document, if provided (check project files)
3. Read the source code unit completely

**Stage 1: Outcome Path Analysis**
- Confirm by specifying the number of outcome paths in the unit.
- This is analysis of EIs, not callables.
- Generate a file of these results so that you do not have to redo the work if there is a problem.
**Stage 2: EI ID Assignment**
- Generate a file of these results so that you do not have to redo the work if there is a problem.
- Confirm by specifying the number of EI IDs assigned.
**Stage 3: Integration Fact Enumeration**
- Generate a file of these results so that you do not have to redo the work if there is a problem.
- Confirm by specifying the number of integration facts enumerated.
**Stage 4: Document Generation**
- Generate each of the three documents separately as interim files for later concatenation.
- Generate it as a file that you can validate in the next step rather than re-creating it.
**Stage 5: Schema Validation**
- You tend to claim that this is complete before you actually do it. Don't.

## Output Format

Your ledger response must be:

```yaml
docKind: derived-ids
# ... Document 1 content ...
---
docKind: ledger
# ... Document 2 content ...
---
docKind: ledger-generation-review
# ... Document 3 content ...
```

There is one circumstance where you can alter the ledger response. In the event
that, due to a large number of EI IDs and integration facts, the ledger response
would exceed the token limit, you may need to break it into multiple documents,
and provide the three documents separately.

Before you output anything, verify:
- [ ] Read the entire spec? (Yes/No - internal check only)
- [ ] Read the entire source unit? (Yes/No - internal check only)
- [ ] Stage 1 complete for all callables?
- [ ] Stage 2 complete for all callables?
- [ ] Stage 3 complete for all callables?
- [ ] Stage 4 complete (all 3 documents)?
- [ ] Stage 5 complete (validation passed)?

If all checks pass: Output the ledger YAML.
If any check fails: Complete that stage first.

---

**NOW EXECUTE THE PROCEDURE.**
