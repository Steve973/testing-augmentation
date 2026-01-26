# Unit Ledger Language Guide: Python

**Language Version(s):** Python 3.10+  
**Companion to:** Unit Ledger Generation Procedure v1.0.0  
**Last Updated:** January 24, 2026

## Purpose

This guide provides language-specific patterns and examples for applying the
Unit Ledger Generation Procedure to Python code. It does NOT replace the core
procedure, so be sure to read that first.

## 1. Language-Specific Context

### 1.1 Compilation/Execution Model
- **Interpreted:** Python code is compiled to bytecode at runtime and executed
  by the interpreter
- **Dynamic typing:** Type hints are optional and not enforced at runtime
- **EI enumeration impact:** Focus on observable execution paths in the source
  code, not bytecode. Type hints inform integration contracts but don't create
  branches.

### 1.2 Control Flow Constructs
Quick reference of what creates EIs in Python:
- **Conditionals:** `if`/`elif`/`else`, ternary expressions
  (`x if condition else y`)
- **Loops:** `for`, `while`, comprehensions with filters
- **Exception handling:** `try`/`except`/`else`/`finally`, context managers
- **Pattern matching:** `match`/`case` (Python 3.10+)
- **Short-circuit evaluation:** `and`, `or` operators (single line = single
  conditional)
- **Walrus operator:** `:=` in conditionals (treated as part of condition)

### 1.3 Unit Boundary

**Unit Definition**: In Python, a unit is widely considered to be a single `.py`
file. All functions, classes, and methods defined in the same `.py` file are
considered part of the same unit. Calls between elements within the same `.py`
file are NOT integration points.

While this can be interpreted differently across different projects and
different teams, it is the assumption in this guide. For consistency and for
convention, we recommend that implementations should follow this convention.

Rationale: This aligns with Python's module system, import conventions, and
typical testing practices where a `test_X.py` file tests all of `X.py` as a
cohesive unit.

## 2. Identifying Execution Items

### 2.1 Simple Statements (1 EI per line)

#### 2.1.1 Variable Assignment
##### Source Code
```python
x = calculate_value()
```

##### Outcome Path Analysis
```yaml
outcome_map:
  42: ["executes: x = calculate_value()"]
```

##### EI ID Assignment
```yaml
ei_mappings:
  - id: C000F001E0001
    line: 42
    outcome: "executes: x = calculate_value()"
```

##### YAML Representation
```yaml
branches:
  - id: C000F001E0001
    condition: 'executes'
    outcome: 'x = calculate_value()'
```

#### 2.1.2 Method/Function Calls
Single EI: the call executes.

#### 2.1.3 Return Statements
Single EI: the return executes.

#### 2.1.4 Nested Operations (Operations as Parameters)

When operations appear as parameters to other operations, each operation
represents at least one distinct EI.

##### What Counts as an Operation
- Method/function calls: `func(other_func())`
- Comprehensions: `process([x for x in items])`
- Property access with `@property` decorator (if it executes code)

##### What Does NOT Count
- Variables: `func(my_var)` - only 1 EI
- Literals: `func(42, "test")` - only 1 EI

##### Source Code
```python
# Example: Method call with method call parameter
normalized = _normalize(self.to_mapping())
```

##### EI Count
At least 2 EIs (analyze each operation separately):
- `self.to_mapping()` executes
- `_normalize(...)` executes

##### Determining Exact EI Count

**If the operation is in this unit:**
Analyze it directly using the normal decision process. If `to_mapping()` has 3
possible outcomes, it creates 3 EIs.

**If the operation is an integration (not in this unit):**
Apply reasonable analysis:
- Well-known operations (stdlib): Use documented behavior (e.g., `json.loads()`
  can raise)
- Other integrations: Assume minimum success/failure outcomes
- Document assumptions in findings

##### Outcome Path Analysis
```yaml
outcome_map:
  94: ["self.to_mapping() executes successfully",
       "_normalize(...) executes with result"]
```

##### Integration Facts
If operations are integrations, track them in Stage 3. In this example:
- `_normalize()` is interunit (function *not* in this module) → integration fact
- `self.to_mapping()` is in this class → NOT an integration fact

To clarify, **any** operation within the same unit is **not** an integration
point/fact, so it should never be captured as one. Any operation that crosses
units (i.e., is physically located in a different `.py` file) is an integration
point, so it should be captured as one.

##### More Examples

**Multiple nested calls:**
```python
result = validate(parse(fetch(url)))
```
At least 3 EIs: `fetch()`, then `parse()`, then `validate()`

**Variable as parameter:**
```python
result = process(my_variable)
```
Only 1 EI - variables don't create additional EIs

**Mixed:**
```python
result = outer(inner(), simple_var)
```
At least 2 EIs: `inner()` and `outer()` - the variable doesn't add an EI

### 2.2 Conditional Constructs

#### 2.2.1 If/Else Statements
##### Source Code
```python
if user.is_authenticated:
    grant_access()
else:
    deny_access()
```

##### Outcome Path Analysis
```yaml
outcome_map:
  10: ["user.is_authenticated true → enters if block",
       "user.is_authenticated false → enters else block"]
```

##### EI Assignment
2 EIs: one for true path, one for false path.

#### 2.2.2 If Without Else
Creates 2 EIs:
- Condition true → enters block
- Condition false → skips to next line

#### 2.2.3 If/Elif/Else Chains
Each `if` or `elif` creates 2 EIs (true/false). Final `else` creates 1 EI.

For N conditionals + else: 2N + 1 EIs total.

#### 2.2.4 Match/Case (Python 3.10+)
##### Source Code
```python
match status_code:
    case 200:
        return "OK"
    case 404:
        return "Not Found"
    case _:
        return "Unknown"
```

##### EI Count
One EI per case (including default `_`). This example: 3 EIs.

#### 2.2.5 Ternary Operators
##### Source Code
```python
message = "Valid" if is_valid else "Invalid"
```

##### EI Count
2 EIs: one for true branch, one for false branch.

### 2.3 Loops

#### 2.3.1 For Loops
##### Source Code
```python
for item in collection:
    process(item)
```

##### EI Count
2 EIs:
- empty collection → 0 iterations
- collection has items → 1+ iterations

**Note:** The loop creates execution items based on whether it iterates, not on
iteration count.

#### 2.3.2 While Loops
Similar to for loops: 2 EIs based on initial condition (true/false).

#### 2.3.3 For-Else
##### Source Code
```python
for item in items:
    if item.matches(criteria):
        return item
else:
    return None
```

##### EI Count
3 outcomes:
- items empty → else executes immediately
- Loop completes without break → else executes
- Loop breaks → else skipped

#### 2.3.4 Loop Control (break/continue)
`break` and `continue` statements each create 1 EI when executed. The conditions
that trigger them create their own EIs.

### 2.4 Collection Operations

#### 2.4.1 List Comprehensions with Filter
##### Source Code
```python
valid_items = [item for item in data if item.is_valid()]
```

##### EI Count
3 EIs (standard pattern for filtered comprehensions):
- data empty → result = []
- data has items, all filtered out → result = []
- data has items, some pass filter → result populated

#### 2.4.2 List Comprehension without Filter
```python
squares = [x * x for x in numbers]
```

##### EI Count
2 EIs:
- numbers empty → result = []
- numbers has items → result populated

#### 2.4.3 Dictionary/Set Comprehensions
Follow same patterns as list comprehensions (3 EIs with filter, 2 without).

#### 2.4.4 Generator Expressions
Same EI counts as comprehensions, but lazy evaluation.

### 2.5 Exception Handling

#### 2.5.1 Try/Except with Single Handler
##### Source Code
```python
try:
    result = parse_json(raw_data)
except JSONDecodeError:
    result = None
```

##### EI Count
3 EIs minimum:
- parse_json succeeds → result assigned (1 EI)
- parse_json raises JSONDecodeError → enters handler (1 EI)
- Handler body executes (1 EI)

#### 2.5.2 Try/Except with Multiple Handlers
Each additional except clause adds 1 EI for entering that handler, plus EIs for
handler body.

#### 2.5.3 Try/Except/Else/Finally
- `else` block: Creates 1 EI, only executes if try succeeds
- `finally` block: Always creates EIs for its execution (runs regardless of
  exceptions)

#### 2.5.4 Context Managers (with statement)
##### Source Code
```python
with open(filename) as f:
    data = f.read()
```

##### EI Count
Minimum 2 EIs:
- Context manager enters successfully
- Context manager raises exception during entry

### 2.6 Null/Optional Handling

#### 2.6.1 None Checks
Standard `if` pattern: 2 EIs for None vs not-None.

#### 2.6.2 Walrus Operator
##### Source Code
```python
if (result := compute_value()) is not None:
    process(result)
```

##### EI Count
2 EIs: result is None vs not None.

**Note:** The assignment happens in both cases; the branching is on the result.

### 2.7 Async/Await Patterns

#### 2.7.1 Async Functions
The `async def` is captured in modifiers, doesn't create additional EIs.

`await` expressions treated like regular calls for EI enumeration.

#### 2.7.2 Async Context Managers
Same 2-EI pattern as synchronous context managers.

## 3. Identifying Integration Points

### 3.1 Import Patterns

#### Static Imports
```python
import json
from pathlib import Path
```

**Do NOT create integration facts** - these are module-level declarations.

#### Dynamic Imports
```python
module = importlib.import_module(f"plugins.{plugin_name}")
```

**DO create integration facts** - this is runtime behavior.

### 3.2 Method Calls

#### Instance Method Calls (Interunit)
##### Source Code
```python
validator = DataValidator()
return validator.validate(data)
```

##### Integration Fact
```yaml
integration:
  interunit:
    - id: IC000F029E0002
      target: DataValidator.validate
      kind: call
      signature: 'validator.validate(data)'
      executionPaths:
        - [C000F029E0001, C000F029E0002]
```

#### Constructor Calls
Use `kind: construct` for class instantiation.

### 3.3 Standard Library Boundaries

#### 3.3.1 Filesystem Operations
```python
with open(path, 'r') as f:
    content = f.read()
```

**Boundary fact:**
- target: `open`
- kind: `io`
- boundary.kind: `filesystem`
- boundary.operation: `read`

#### 3.3.2 Network Operations
```python
response = requests.get(url)
```

**Boundary fact:**
- target: `requests.get`
- kind: `call`
- boundary.kind: `network`
- boundary.protocol: `http`

#### 3.3.3 Database Operations
```python
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

**Boundary fact:**
- target: `cursor.execute`
- kind: `call`
- boundary.kind: `database`
- boundary.operation: `query`

#### 3.3.4 Environment Variables
```python
api_key = os.getenv("API_KEY")
```

**Boundary fact:**
- target: `os.getenv`
- kind: `call`
- boundary.kind: `env`
- boundary.operation: `read`

#### 3.3.5 Time/Clock Operations
```python
timestamp = datetime.now()
```

**Boundary fact:**
- target: `datetime.now`
- kind: `call`
- boundary.kind: `clock`
- boundary.operation: `read`

#### 3.3.6 Random Number Generation
```python
value = random.random()
```

**Boundary fact:**
- target: `random.random`
- kind: `call`
- boundary.kind: `randomness`
- boundary.operation: `generate`

### 3.4 Framework-Specific Patterns

#### Django ORM
```python
User.objects.filter(is_active=True)
```

Creates database boundary integration.

#### Flask/FastAPI Decorators
Decorators themselves go in the `decorators` field, not as integration facts.
Framework dispatch is external to the unit.

## 4. Edge Cases and Subtleties

### 4.1 Implicit Execution

#### Properties (`@property`)
Treat Python properties (`@property` decorated methods) as callables, since they
execute code when they are invoked or accessed.

**Properties are NOT integration points when accessed on `self` or other 
instances defined in the same unit.** For example, `self.identifier`, where 
`identifier` is a `@property` in the same class, creates an EI for the property 
access, but NOT an integration fact. It is an integration point **only** when
accessing a property on an object from a different unit (i.e., different `.py`
file).

#### Magic Methods (`__str__`, `__eq__`, etc.)
Enumerate like regular methods.

#### Decorators
Captured in `decorators` field, not as EIs within the decorated function.

### 4.2 Multi-line Expressions

#### Line Continuation
Assign EI to the first physical line of a logical line.

```python
result = some_function(arg1, arg2, arg3, arg4)
```

EI assigned to line with `result =`.

#### Chained Method Calls
```python
result = (data_frame
          .filter(lambda x: x.is_valid)
          .map(lambda x: x.value))
```

Assign an EI to the first line. If the chain includes filters, enumerate filter
outcomes.

### 4.3 Short-Circuit Evaluation

#### Logical AND/OR
```python
if user and user.is_admin:
    grant_access()
```

Creates 2 EIs (condition true/false), NOT 3 or 4. The short-circuit is an
implementation detail, not separate branch.

### 4.4 Lazy Evaluation

#### Generators
```python
def generate_numbers(n: int):
    for i in range(n):
        if i % 2 == 0:
            yield i
```

Enumerate the generator function's EIs normally. The for loop and if each
create their EIs.

### 4.5 Type System

#### Type Hints
- Captured in `TypeRef` structures
- Don't create EIs or affect branching
- Inform integration contracts

#### Union Types
`X | Y` doesn't create branches. Runtime `isinstance()` checks create branches.

## 5. Worked Examples

### 5.1 Input Validation with Multiple Checks

```python
def validate_user_input(username: str, age: int) -> tuple[bool, str]:
    if not username:
        return False, "Username required"
    if len(username) < 3:
        return False, "Username too short"
    if age < 13:
        return False, "Must be 13 or older"
    if age > 120:
        return False, "Invalid age"
    return True, ""
```

**Total EIs:** 9
- Line 2: 2 EIs (username check)
- Line 4: 2 EIs (length check)
- Line 6: 2 EIs (minimum age)
- Line 8: 2 EIs (maximum age)
- Line 10: 1 EI (success return)

**Integration facts:** None (pure validation)

### 5.2 Exception Handling with Multiple Handlers

```python
def load_config(path: str) -> dict:
    try:
        file_obj = open(path, 'r')
        content = file_obj.read()
        return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    finally:
        if file_obj:
            file_obj.close()
```

**Key EI points:**
- open() creates 3 EIs: succeeds, raises FileNotFoundError, raises other
  exception
- json.loads() creates 3 EIs: succeeds, raises JSONDecodeError, raises other
  exception
- the if statement in the `finally` block creates 2 EIs

**Integration facts:**
- open() → filesystem boundary
- json.loads() → interunit call

### 5.3 List Comprehension with API Call

```python
def fetch_active_user_emails(api_url: str) -> list[str]:
    try:
        response = requests.get(f"{api_url}/users")
        response.raise_for_status()
    except requests.RequestException:
        return []
    
    users = response.json()
    return [user['email'] for user in users if user.get('is_active', False)]
```

**Key points:**
- Try block: requests.get and raise_for_status each create exception EIs
- List comprehension: 3 EIs (empty, all filtered, some pass)

**Integration facts:**
- requests.get() → network boundary

### 5.4 Sequential Independent Conditionals

```python
def to_dict(self) -> dict[str, Any]:
    result = {}
    if self.db_host is not None:
        result['db_host'] = self.db_host
    if self.cache_enabled is not None:
        result['cache_enabled'] = self.cache_enabled
    if self.log_level is not None:
        result['log_level'] = self.log_level
    return result
```

**EI count:** 11
- result = {}: 1 EI
- Each if: 2 EIs (check + assignment)
- 3 assignments: 3 EIs
- return: 1 EI

**Important:** Three independent conditionals means that execution can take
2³ = 8 different paths, but we enumerate the branches at each line, not all
path combinations.

### 5.5 Async with Concurrent Operations

```python
async def fetch_multiple_resources(urls: list[str]) -> list[dict]:
    if not urls:
        return []
    
    async def fetch_one(url: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
        except asyncio.TimeoutError:
            return {"error": "timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    tasks = [fetch_one(url) for url in urls]
    return await asyncio.gather(*tasks)
```

**Structure:**
- Outer function has EIs for if check and async operations
- Nested async function has EIs for try/except handlers
- Integration facts for aiohttp calls and asyncio.gather

## 6. Quick Reference

### 6.1 Construct → EI Count Mapping

| Construct                 | Pattern               | EI Count | Notes                            |
|---------------------------|-----------------------|----------|----------------------------------|
| Assignment                | `x = value`           | 1        | Single execution                 |
| If/else                   | `if ... else`         | 2        | True/false paths                 |
| If without else           | `if cond:`            | 2        | Enter/skip                       |
| If/elif/else (N branches) | N conditions          | 2N+1     | Each condition: 2, final else: 1 |
| Ternary                   | `a if c else b`       | 2        | True/false                       |
| Match/case (N cases)      | `match:`              | N        | One per case                     |
| For loop                  | `for x in y:`         | 2        | 0 iter / ≥1 iter                 |
| While loop                | `while cond:`         | 2        | Initial true/false               |
| For-else                  | `for ... else:`       | 3        | Empty, completes, breaks         |
| Try/except (N handlers)   | Multiple except       | N+1      | Success + each handler           |
| With statement            | `with x as y:`        | 2        | Enters / raises                  |
| List comp w/ filter       | `[x for x in y if z]` | 3        | Empty, all filtered, some pass   |
| List comp no filter       | `[x for x in y]`      | 2        | Empty / has items                |

### 6.2 Common Boundary Integrations

| Pattern     | Boundary Kind | Example            | Notes             |
|-------------|---------------|--------------------|-------------------|
| File I/O    | filesystem    | `open()`           | read/write/append |
| HTTP        | network       | `requests.get()`   | REST APIs         |
| Database    | database      | `cursor.execute()` | SQL queries       |
| Environment | env           | `os.getenv()`      | Config values     |
| Time        | clock         | `datetime.now()`   | Current time      |
| Random      | randomness    | `random.random()`  | Non-deterministic |
| Subprocess  | subprocess    | `subprocess.run()` | External programs |

### 6.3 Integration Kind Mapping

| Pattern             | Integration Kind | Usage                         |
|---------------------|------------------|-------------------------------|
| Function call       | call             | Most invocations              |
| Class instantiation | construct        | `ClassName()`                 |
| Dynamic import      | import           | `importlib.import_module()`   |
| Callback passed     | dispatch         | Function as argument          |
| Direct I/O          | io               | `open()`, `read()`, `write()` |

### 6.4 Python-Specific Reminders

**Truthiness:**
- Falsy: `None`, `False`, `0`, `0.0`, `""`, `[]`, `{}`, `()`
- Everything else is truthy

**Exception Hierarchy:**
- Specific exceptions before general ones
- `Exception` catches most (not `SystemExit`, `KeyboardInterrupt`)

**Async:**
- `async def` in modifiers, doesn't create extra EIs
- `await` treated like regular calls
- `async with` same 2 outcomes as regular `with`

**Comprehensions:**
- With filter: always 3 outcomes
- Without filter: always 2 outcomes
- Nested: consider carefully, may be complex

**Type Hints:**
- Captured in TypeRef, don't create EIs
- Runtime checks (`isinstance`) create EIs
