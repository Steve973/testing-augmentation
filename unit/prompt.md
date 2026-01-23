# Unit Ledger Generation: Execution Instructions

## Your Role

You are executing the Unit Ledger Generation Procedure as specified. This is a **procedural task**,
not an analytical one. Follow the spec exactly as written.

## Authoritative Sources

**THE SPEC (unit-ledger-spec.md):** The controlling algorithm. Follow it exactly.
- Read it completely before starting
- Treat it as executable instructions
- Do not reinterpret, summarize, or improve it
- If anything is unclear, use the most direct interpretation and continue

**THE SCHEMA (unit-ledger-spec_schema.json):** Validation only.
- Use ONLY after generation is complete
- Do not derive generation rules from it
- Do not reference it during generation
- It validates your output, nothing more

**If spec and schema conflict:** Follow the spec for generation. Let validation catch conflicts.
Record any issues in Document 3 (findings).

## Task Definition

**OBJECTIVE:** Generate the Unit Ledger for the provided source code unit.

**DELIVERABLE:** Three-document YAML file that:
1. Conforms to the spec procedure
2. Validates against the schema
3. Contains no placeholder text

**MODE:** Direct execution - observe code, apply procedure, emit YAML.

## Core Execution Principles

### 1. Observation Over Analysis
- Report what exists in the code
- Map observed facts to spec-required fields
- Do not analyze, debate, or interpret

### 2. Progress Over Perfection
- If uncertain between two spec-compliant options, choose one and continue
- Do not revisit decisions unless validation fails
- Forward progress is mandatory

### 3. Procedure Over Commentary
- Execute the 5 stages in order
- Do not explain what you're doing
- Do not discuss intentions or plans
- Output only the ledger YAML (and findings in Document 3)

### 4. Completeness Over Shortcuts
- Enumerate ALL execution items (every line, every outcome)
- Enumerate ALL execution paths to integration points
- Do not skip "obvious" cases
- Thoroughness is non-negotiable

## What NOT to Output

Do not include any of these in your response:
- "I will..." / "I'm going to..." / "I should..." / "I need to..."
- "Let me..." / "First, I'll..." / "Next, I'll..."
- "I notice..." / "I see..." / "It seems..." / "It appears..."
- "I think..." / "Probably..." / "Likely..." / "Maybe..."
- "Worth noting..." / "Interestingly..." / "However..."
- Planning statements
- Procedural commentary
- Spec interpretations
- Schema discussions
- Edge case debates
- Validation strategy

**Exception:** Document 3 (Review) may contain findings about the generation process,
recorded as structured findings per the spec.

## Required Execution Sequence

**Before you begin:**
1. Read the entire spec document (do this, don't announce it)
2. Read the source code unit completely

**Stage 1: Outcome Path Analysis**
- For each callable, analyze line-by-line
- Identify all distinct outcome paths per line
- Build outcome maps
- Verify: every executable line analyzed

**Stage 2: EI ID Assignment**
- Assign sequential IDs to all outcomes
- Follow ID grammar rules precisely
- Verify: ID count matches outcome count

**Stage 3: Integration Fact Enumeration**
- Identify all integration points
- Trace ALL execution paths to each integration
- Build integration facts with executionPaths
- Verify: all paths end with integration's EI ID

**Stage 4: Document Generation**
- Generate Document 1 (Derived IDs)
- Generate Document 2 (Ledger)
- Generate Document 3 (Review)
- Verify: structure is complete

**Stage 5: Schema Validation**
- Validate YAML against schema
- If validation fails: repair loop (max 5 iterations)
- Each repair: minimal fix for reported errors only
- Verify: validation passes

## Critical Rules

1. **Spec Authority:** The spec defines generation. Schema only validates.

2. **No Schema-Driven Generation:** Do not look at schema patterns to decide how to generate content.

3. **Read Once, Execute:** Read spec completely first, then execute stages sequentially.
   No re-reading for "clarification."

4. **Optional Field Handling:** Omit empty optional fields. Do not emit placeholders like "TBD" or "null."

5. **Evidence Tethering:** Every ledger item must correspond to actual code in the unit.

6. **Integration Enumeration:** If code contains a call/boundary crossing and the spec requires it, record it.
   Do not debate whether it "counts."

7. **Execution Path Completeness:** For N independent conditionals before an integration,
   enumerate 2^N paths (Cartesian product).

8. **Inconsistency Handling:** If you notice spec inconsistencies, use the most direct interpretation and continue.
   No commentary.

9. **Single-Quote Escaping:** Code strings in YAML must:
   - Be enclosed in single quotes
   - Double any internal single quotes
   - Join multi-line code into a single line

10. **Validation Loop:** Max 5 repair iterations. Stop when validation passes or max reached.

## Output Format

Your entire response must be:

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

**Nothing before the YAML. Nothing after the YAML.**

## Common Pitfalls to Avoid

❌ Announcing stages: "Now I'll do Stage 1..."
✅ Just execute Stage 1

❌ Explaining decisions: "I chose this because..."
✅ Just make the choice and continue

❌ Incomplete enumeration: "The main path is..."
✅ Enumerate ALL paths, ALL EIs

❌ Schema-based generation: "The schema shows..."
✅ Follow the spec, ignore schema until validation

❌ Placeholder text: "TBD", "TODO", "???"
✅ Omit the field or provide actual value

❌ Verbose outcomes: Long explanations
✅ Concise outcome descriptions

❌ Missing executionPaths: Integration without paths
✅ ALL paths enumerated completely

## Execution Checkpoint

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

Begin with Stage 1 for the first callable in the unit.