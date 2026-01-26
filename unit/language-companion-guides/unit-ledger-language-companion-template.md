# Unit Ledger Language Guide: [LANGUAGE_NAME]

**Language Version(s):** [e.g., Python 3.10+, Java 17+]  
**Companion to:** Unit Ledger Generation Procedure v[VERSION]  
**Last Updated:** [DATE]

## Purpose

This guide provides language-specific patterns and examples for applying the
Unit Ledger Generation Procedure to [LANGUAGE_NAME] code. It does NOT replace
the core procedure—read that first.

## 1. Language-Specific Context

### 1.1 Compilation/Execution Model
- [Compiled/Interpreted/JIT/etc.]
- [How this affects EI enumeration]

### 1.2 Control Flow Constructs
Quick reference of what creates EIs in this language:
- **Conditionals:** if/else, switch/match, ternary
- **Loops:** for, while, do-while, iterators
- **Exception handling:** try/catch/finally, throws
- **Pattern matching:** [if applicable]
- **Null safety:** [if applicable]
- **Short-circuit evaluation:** [if applicable]

### 1.3 Unit Boundaries
Provide a definition of, and explain what constitutes, a unit boundary in this
language and include the rationale for the stated unit boundary distinction.

## 2. Identifying Execution Items

### 2.1 Simple Statements (1 EI per line)

#### 2.1.1 Variable Assignment
##### 2.1.1.1 Source Code
[Code example]

##### 2.1.1.2 Outcome Path Analysis
[Outcome map showing single outcome]

##### 2.1.1.3 EI ID Assignment
[EI ID mapping]

##### 2.1.1.4 YAML Representation (Document 2 excerpt)
[YAML snippet]

#### 2.1.2 Method/Function Calls
[Same 4-part structure]

#### 2.1.3 Return Statements
[Same 4-part structure]

### 2.2 Conditional Constructs

#### 2.2.1 If/Else Statements
##### 2.2.1.1 Source Code
```language
if (condition) {
    // true branch
} else {
    // false branch
}
```

##### 2.2.1.2 Outcome Path Analysis
```yaml
outcome_map:
  [line_num]: [
    "condition true → enters if block",
    "condition false → enters else block"
  ]
```

##### 2.2.1.3 EI ID Assignment
```yaml
ei_mappings:
  - id: C000F001E0001
    line: [line_num]
    outcome: "condition true → enters if block"
  - id: C000F001E0002
    line: [line_num]
    outcome: "condition false → enters else block"
```

##### 2.2.1.4 YAML Representation (Document 2 excerpt)
```yaml
branches:
  - id: C000F001E0001
    condition: 'if condition'
    outcome: 'enters if block'
  - id: C000F001E0002
    condition: 'else'
    outcome: 'enters else block'
```

#### 2.2.2 If Without Else
##### 2.2.2.1 Source Code
[Code example]

##### 2.2.2.2 Outcome Path Analysis
[Outcome map: true → enter, false → skip to next line]

##### 2.2.2.3 EI ID Assignment
[EI IDs]

##### 2.2.2.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.2.3 If/Elif/Else Chains
##### 2.2.3.1 Source Code
[Code example]

##### 2.2.3.2 Outcome Path Analysis
[Outcome map showing each condition's outcomes]

##### 2.2.3.3 EI ID Assignment
[EI IDs for each outcome]

##### 2.2.3.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.2.4 Switch/Match Expressions
##### 2.2.4.1 Source Code
[Code example with multiple cases]

##### 2.2.4.2 Outcome Path Analysis
[One outcome per case, plus default]

##### 2.2.4.3 EI ID Assignment
[EI IDs]

##### 2.2.4.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.2.5 Ternary Operators
##### 2.2.5.1 Source Code
[Code example]

##### 2.2.5.2 Outcome Path Analysis
[Two outcomes: true value, false value]

##### 2.2.5.3 EI ID Assignment
[EI IDs]

##### 2.2.5.4 YAML Representation (Document 2 excerpt)
[YAML]

### 2.3 Loops

#### 2.3.1 For Loops
##### 2.3.1.1 Source Code
[Code example]

##### 2.3.1.2 Outcome Path Analysis
[0 iterations vs ≥1 iterations]

##### 2.3.1.3 EI ID Assignment
[EI IDs]

##### 2.3.1.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.3.2 While Loops
##### 2.3.2.1 Source Code
[Code example]

##### 2.3.2.2 Outcome Path Analysis
[Initial condition false vs true]

##### 2.3.2.3 EI ID Assignment
[EI IDs]

##### 2.3.2.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.3.3 Do-While Loops (if applicable)
[Same 4-part structure]

#### 2.3.4 Enhanced For/Foreach Loops
[Same 4-part structure]

#### 2.3.5 Loop Control (break/continue)
[Same 4-part structure - note these often don't create their own EIs but affect reachability]

### 2.4 Collection Operations

#### 2.4.1 List Comprehensions (if applicable)
##### 2.4.1.1 Source Code
[Code example]

##### 2.4.1.2 Outcome Path Analysis
[Empty, all filtered, some pass - 3 outcomes]

##### 2.4.1.3 EI ID Assignment
[EI IDs]

##### 2.4.1.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.4.2 Stream Operations (if applicable)
[Same 4-part structure]

#### 2.4.3 Map/Filter/Reduce (if applicable)
[Same 4-part structure]

### 2.5 Exception Handling

#### 2.5.1 Try/Catch with Single Handler
##### 2.5.1.1 Source Code
[Code example]

##### 2.5.1.2 Outcome Path Analysis
[Try block line: succeeds, throws exception]

##### 2.5.1.3 EI ID Assignment
[EI IDs]

##### 2.5.1.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.5.2 Try/Catch with Multiple Handlers
[Same 4-part structure]

#### 2.5.3 Try/Catch/Finally
[Same 4-part structure]

#### 2.5.4 Try-with-Resources (if applicable)
[Same 4-part structure]

### 2.6 Null/Optional Handling

#### 2.6.1 Null-Conditional Operator (?. or similar)
##### 2.6.1.1 Source Code
[Code example]

##### 2.6.1.2 Outcome Path Analysis
[Null vs non-null outcomes]

##### 2.6.1.3 EI ID Assignment
[EI IDs]

##### 2.6.1.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.6.2 Null-Coalescing (?? or similar)
[Same 4-part structure]

#### 2.6.3 Optional.map/flatMap (if applicable)
[Same 4-part structure]

### 2.7 Async/Await Patterns (if applicable)

#### 2.7.1 Async Function Calls
##### 2.7.1.1 Source Code
[Code example]

##### 2.7.1.2 Outcome Path Analysis
[How async affects EI enumeration]

##### 2.7.1.3 EI ID Assignment
[EI IDs]

##### 2.7.1.4 YAML Representation (Document 2 excerpt)
[YAML]

#### 2.7.2 Await with Error Handling
[Same 4-part structure]

## 3. Identifying Integration Points

### 3.1 Import Patterns
#### 3.1.1 Standard Imports
##### 3.1.1.1 Source Code
[Import syntax]

##### 3.1.1.2 When It Creates Integration Facts
[Usually doesn't unless dynamic]

##### 3.1.1.3 Example Integration Fact (if applicable)
[YAML]

#### 3.1.2 Dynamic Imports (if applicable)
[Full structure if relevant]

### 3.2 Method Calls

#### 3.2.1 Instance Method Calls (Interunit)
##### 3.2.1.1 Source Code
[Code example]

##### 3.2.1.2 Integration Fact Analysis
[Identify target, kind, signature]

##### 3.2.1.3 Execution Paths
[How to trace paths to the integration]

##### 3.2.1.4 YAML Representation (Document 2 excerpt)
[Integration fact YAML]

#### 3.2.2 Static Method Calls
[Same 4-part structure]

#### 3.2.3 Constructor Calls
[Same 4-part structure]

### 3.3 Standard Library Boundaries

#### 3.3.1 Filesystem Operations
##### 3.3.1.1 Source Code
[Common patterns: open, read, write]

##### 3.3.1.2 Integration Fact Analysis
[boundary.kind = filesystem]

##### 3.3.1.3 Execution Paths
[Path tracing]

##### 3.3.1.4 YAML Representation (Document 2 excerpt)
[Boundary integration YAML]

#### 3.3.2 Network Operations
[Same 4-part structure: HTTP, sockets, etc.]

#### 3.3.3 Database Operations
[Same 4-part structure: query, transaction]

#### 3.3.4 Environment Variables
[Same 4-part structure]

#### 3.3.5 Time/Clock Operations
[Same 4-part structure]

#### 3.3.6 Random Number Generation
[Same 4-part structure]

### 3.4 Framework-Specific Patterns

#### 3.4.1 [Framework Name - e.g., Spring/Django]
##### 3.4.1.1 Dependency Injection
[How DI calls are represented]

##### 3.4.1.2 Annotations/Decorators
[Integration implications]

##### 3.4.1.3 Example Integration Facts
[YAML examples]

### 3.5 Reflection and Metaprogramming (if applicable)

#### 3.5.1 Dynamic Method Invocation
[Same 4-part structure]

#### 3.5.2 Class Loading/Instantiation
[Same 4-part structure]

## 4. Edge Cases and Subtleties

### 4.1 Implicit Execution

#### 4.1.1 Property Getters/Setters
##### Description
[When properties execute code]

##### Source Code Example
[Code]

##### EI Enumeration Guidance
[Whether/how to count]

##### YAML Example
[If applicable]

#### 4.1.2 Operator Overloading
[Same structure]

#### 4.1.3 Decorators/Annotations
[Same structure]

### 4.2 Multi-line Expressions

#### 4.2.1 Line Continuation
##### Description
[How language handles multi-line expressions]

##### Guidance
[Which line gets the EI]

##### Example
[Code + outcome map]

#### 4.2.2 Chained Method Calls
[Same structure]

### 4.3 Short-Circuit Evaluation

#### 4.3.1 Logical AND (&&)
##### Description
[How short-circuiting works]

##### EI Counting Rule
[Single line = single conditional outcomes, not per operand]

##### Example
[Code + EI count]

#### 4.3.2 Logical OR (||)
[Same structure]

### 4.4 Lazy Evaluation (if applicable)

#### 4.4.1 Generators/Yield
[Structure as needed]

#### 4.4.2 Lazy Collections
[Structure as needed]

### 4.5 Type System Interactions (if applicable)

#### 4.5.1 Generics and Type Erasure
[When relevant to EI enumeration]

#### 4.5.2 Union Types
[If affects branching]

## 5. Worked Examples

### 5.1 [Example Name - e.g., "Input Validation with Multiple Checks"]

#### 5.1.1 Source Code
[Complete function/method]

#### 5.1.2 Stage 1: Outcome Path Analysis
[Full outcome map]

#### 5.1.3 Stage 2: EI ID Assignment
[Complete EI mappings]

#### 5.1.4 Stage 3: Integration Facts (if any)
[Integration facts with execution paths]

#### 5.1.5 Stage 4: Document Generation
##### Document 1 Excerpt (Derived IDs)
[Relevant portions]

##### Document 2 Excerpt (Ledger)
[Complete Entry with CallableSpec]

##### Document 3 (Review)
[Any findings]

### 5.2 [Another Example - e.g., "Exception Handling with Multiple Handlers"]
[Same full structure]

### 5.3 [Another Example - e.g., "Stream Processing with Filters"]
[Same full structure]

[Continue with 5-8 diverse examples covering:
- Tricky conditional patterns
- Complex loop scenarios
- Integration-heavy code
- Edge cases from Section 4
- Real-world patterns from popular libraries/frameworks]

## 6. Quick Reference

### 6.1 Construct → EI Count Mapping
| Construct                       | Pattern                   | EI Count  | Example                                  |
|---------------------------------|---------------------------|-----------|------------------------------------------|
| Simple assignment               | `x = value`               | 1         | Line executes                            |
| If without else                 | `if condition`            | 2         | True → enter, False → skip               |
| If/else                         | `if ... else`             | 2         | True → if, False → else                  |
| If/elif/else (N branches)       | Multiple conditions       | 2N        | Each condition has true/false            |
| Ternary                         | `a ? b : c`               | 2         | True → b, False → c                      |
| For loop                        | `for item in collection`  | 2         | Empty → 0 iter, Has items → ≥1 iter      |
| While loop                      | `while condition`         | 2         | Initially false → 0, Initially true → ≥1 |
| Try/catch (1 handler)           | `try ... catch E`         | 2         | Succeeds, Throws E                       |
| Try/catch (N handlers)          | Multiple catches          | N+1       | Succeeds + each handler                  |
| List comp w/ filter             | `[x for x in lst if ...]` | 3         | Empty, all filtered, some pass           |
| [Language-specific patterns...] | [...]                     | [...]     | [...]                                    |

### 6.2 Common Boundary Integrations
| Pattern                 | Boundary Kind  | Example Target                        | Notes             |
|-------------------------|----------------|---------------------------------------|-------------------|
| File operations         | filesystem     | `open()`, `File.read()`               | read/write/delete |
| HTTP calls              | network        | `requests.get()`, `HttpClient`        | REST, GraphQL     |
| Database queries        | database       | `cursor.execute()`, `Session.query()` | SQL, ORM          |
| Environment access      | env            | `os.getenv()`, `System.getenv()`      | Config values     |
| Time operations         | clock          | `time.now()`, `LocalDateTime.now()`   | Current time      |
| Random generation       | randomness     | `random.random()`, `Math.random()`    | Non-deterministic |
| Subprocess calls        | subprocess     | `subprocess.run()`, `Runtime.exec()`  | External programs |
| [Framework patterns...] | [...]          | [...]                                 | [...]             |

### 6.3 Integration Kind Mapping
| Language Pattern    | Integration Kind  | When to Use                      |
|---------------------|-------------------|----------------------------------|
| Method call         | call              | Most function/method invocations |
| Constructor         | construct         | Object instantiation             |
| Import statement    | import            | (Rarely - only if dynamic)       |
| Delegate/Callback   | dispatch          | Function pointer, lambda passed  |
| File I/O            | io                | Direct read/write operations     |
| [Other patterns...] | [...]             | [...]                            |