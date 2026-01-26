# Unit Ledger Language Guide: Java

**Language Version(s):** Java 17+  
**Companion to:** Unit Ledger Generation Procedure v1.0.0  
**Last Updated:** 2025-01-24

## Purpose

This guide provides language-specific patterns and examples for applying the
Unit Ledger Generation Procedure to Java code. It does NOT replace the core
procedure—read that first.

## 1. Language-Specific Context

### 1.1 Compilation/Execution Model

Java is compiled to bytecode and executed on the JVM. This affects EI
enumeration:
- Static type system: type-based branching resolved at compile time
- Checked exceptions: must be declared or handled, creating explicit control flow
- Method overloading: resolved at compile time (no runtime dispatch EIs)
- Generic type erasure: happens at compile time (no runtime type checking EIs)

### 1.2 Control Flow Constructs

Quick reference of what creates EIs in Java:

- **Conditionals:** if/else, switch/case, ternary (`? :`), switch expressions
  (Java 14+)
- **Loops:** for, enhanced for (foreach), while, do-while
- **Exception handling:** try/catch/finally, try-with-resources
- **Pattern matching:** instanceof with pattern variables (Java 16+), switch
  with patterns (Java 21+)
- **Null safety:** Optional methods (map, flatMap, orElse, etc.)
- **Short-circuit evaluation:** && (AND), || (OR) operators

### 1.3 Unit Boundaries
**Unit Definition**: In Java, a unit is an item (typically, it is a class or
interface) that is compiled into a single `.class` file, regardless of how the
`.java` source file is organized. In addition to a class or an interface, other
constructs are units:
- Enum
- Annotation
- Nested class

As an example, consider how a single `MyClass.java` file could contain many of
these constructs, resulting in many `.class` files that represent distinct
units:

```java
public class MyClass {                                 // → MyClass.class
    
    // Nested static class
    public static class Registry {                     // → MyClass$Registry.class
        private final Map<String, Item> items = new HashMap<>();
    }
    
    // Inner (non-static) class  
    public class Session {                             // → MyClass$Session.class
        public void doWork() {
            // Anonymous class inside a method
            Runnable task = new Runnable() {           // → MyClass$Session$1.class
                @Override
                public void run() {
                    System.out.println("Anonymous magic!");
                }
            };
            
            // Local class inside a method
            class LocalHelper {                        // → MyClass$Session$1LocalHelper.class
                void help() { }
            }
        }
    }
}

// Interface (top-level, package-private)
interface Pluggable {                                  // → Pluggable.class
    void activate();
}

// Enum (top-level, package-private)
enum Status {                                          // → Status.class
    ACTIVE, INACTIVE, PENDING
}

// Annotation definition (top-level, package-private)
@interface Experimental {                              // → Experimental.class
    String since() default "";
}

// Another package-private class
class HelperUtils {                                    // → HelperUtils.class
    static void assist() { }
}
```

Therefore, a single `.java` source file may contain multiple units. 

**Rationale**: This aligns with Java's compilation model (one `.class` file per
type), the JVM's class-loading architecture, and typical testing practices where
a `MyClassTest.java` tests all methods of `MyClass.class` as a cohesive unit. It
also reflects how mocking frameworks (like Mockito) operate at class boundaries
and how dependency injection containers wire classes together.

**Important implications**:
1. When creating unit ledgers, a ledger contains all information for a single
   unit. If a `.java` source file contains multiple units, then one separate
   ledger must be created for each unit. The fact that the unit is designated
   with an ID of `C000` means that only one unit may be present in a ledger.
2. With in the same `.java` source file, if code in one unit calls a method in
   another unit from the same file, then the method call is considered an
   integration.

## 2. Identifying Execution Items

### 2.1 Simple Statements (1 EI per line)

#### 2.1.1 Variable Assignment

##### 2.1.1.1 Source Code
```java
int total = calculateTotal(items);
```

##### 2.1.1.2 Outcome Path Analysis
```yaml
outcome_map:
  42: ["executes: total assigned result of calculateTotal(items)"]
```

##### 2.1.1.3 EI ID Assignment
```yaml
ei_mappings:
  - id: C001M002E0001
    line: 42
    outcome: "executes: total assigned result of calculateTotal(items)"
```

##### 2.1.1.4 YAML Representation (Document 2 excerpt)
```yaml
branches:
  - id: C001M002E0001
    condition: 'executes'
    outcome: 'total = calculateTotal(items)'
```

#### 2.1.2 Method/Function Calls
[Same 4-part structure – single EI for method execution]

#### 2.1.3 Return Statements
[Same 4-part structure – single EI for return]

### 2.2 Conditional Constructs

#### 2.2.1 If/Else Statements

##### 2.2.1.1 Source Code
```java
if (balance > 0) {
    processPayment();
} else {
    handleInsufficientFunds();
}
```

##### 2.2.1.2 Outcome Path Analysis
```yaml
outcome_map:
  10: ["balance > 0 true → enters if block",
       "balance > 0 false → enters else block"]
```

##### 2.2.1.3 EI ID Assignment
```yaml
ei_mappings:
  - id: C001M005E0001
    line: 10
    outcome: "balance > 0 true → enters if block"
  - id: C001M005E0002
    line: 10
    outcome: "balance > 0 false → enters else block"
```

##### 2.2.1.4 YAML Representation (Document 2 excerpt)
```yaml
branches:
  - id: C001M005E0001
    condition: 'if (balance > 0)'
    outcome: 'enters if block, processPayment() called'
  - id: C001M005E0002
    condition: 'else'
    outcome: 'enters else block, handleInsufficientFunds() called'
```

#### 2.2.2 If Without Else
[Same 4-part structure - creates 2 EIs: true enters, false skips]

#### 2.2.3 If/Else If/Else Chains
For N conditions, creates 2N EIs (each condition has a true/false outcome).

#### 2.2.4 Switch/Case Statements (Traditional)

Creates N+1 EIs where N = number of cases (including default).
Fall-through cases should be noted but count as single EI.

#### 2.2.5 Switch Expressions (Java 14+)

##### 2.2.5.1 Source Code
```java
String description = switch (status) {
    case ACTIVE -> "Currently active";
    case INACTIVE -> "Not active";
    case SUSPENDED -> "Temporarily suspended";
    default -> "Unknown status";
};
```

Creates 4 EIs (one per case including default). Note: arrow syntax prevents
fall-through.

#### 2.2.6 Ternary Operators
[Same pattern as if/else - creates 2 EIs]

### 2.3 Loops

#### 2.3.1 For Loops (Traditional)

##### 2.3.1.1 Source Code
```java
for (int i = 0; i < items.size(); i++) {
    process(items.get(i));
}
```

##### 2.3.1.2 Outcome Path Analysis
```yaml
outcome_map:
  70: ["items.size() == 0 → loop body never executes (0 iterations)",
       "items.size() > 0 → loop body executes (≥1 iterations)"]
```

Creates 2 EIs: zero iterations vs. 1+ iterations.

#### 2.3.2 Enhanced For Loops (Foreach)
[Same pattern as traditional for - 2 EIs: empty vs has elements]

#### 2.3.3 While Loops
[Same pattern – 2 EIs: initially false vs initially true]

#### 2.3.4 Do-While Loops
Creates 2+ EIs: body always executes once, then condition determines loop
continuation.

#### 2.3.5 Loop Control (break/continue)
`Break` and `continue` don't create their own EIs but affect reachability. Count
them as outcomes of the conditional that triggers them.

### 2.4 Collection Operations

#### 2.4.1 Stream Operations with Filter

##### 2.4.1.1 Source Code
```java
List<String> valid = items.stream()
    .filter(Item::isValid)
    .map(Item::getName)
    .collect(Collectors.toList());
```

##### 2.4.1.2 Outcome Path Analysis
```yaml
outcome_map:
  125: ["items is empty → valid = []",
        "items not empty but all filtered out → valid = []",
        "items not empty and some pass filter → valid populated"]
```

Creates 3 EIs. Anchor to stream start line. All intermediate operations are
lazy and don't create separate EIs.

#### 2.4.2 Stream with FindFirst/FindAny
[Same 3-outcome pattern: empty, all filtered, some pass]

#### 2.4.3 Stream Reduction Operations
Creates 2 EIs: empty stream returns identity value, non-empty returns reduced
value.

### 2.5 Exception Handling

#### 2.5.1 Try/Catch with Single Handler

##### 2.5.1.1 Source Code
```java
try {
    result = parseData(input);
} catch (ParseException e) {
    logger.error("Parse failed", e);
    result = null;
}
```

##### 2.5.1.2 Outcome Path Analysis
```yaml
outcome_map:
  155: ["parseData succeeds → result assigned",
        "parseData throws ParseException → enters catch handler"]
  157: ["executes: logger.error call"]
  158: ["executes: result = null"]
```

Creates N+M EIs where N=1 for try success, plus M EIs in catch block.

#### 2.5.2 Try/Catch with Multiple Handlers
For N catch blocks, creates N+1 EIs at the try line (success and each exception
type), plus EIs for statements within each handler.

#### 2.5.3 Try/Catch/Finally
`Finally` block always executes. Count EIs within `finally` block normally,
since they execute regardless of exception.

#### 2.5.4 Try-with-Resources

**Important:** Resource creation itself creates 2 EIs (succeeds vs. throws).
Resource is auto-closed even if an exception occurs.

### 2.6 Null/Optional Handling

#### 2.6.1 Optional.map
```java
String name = Optional.ofNullable(user)
    .map(User::getName)
    .orElse("Unknown");
```

Creates 2 EIs: empty → default value, present → mapped value.

#### 2.6.2 Optional.flatMap
Creates 3 EIs: empty → empty, present but inner empty → empty, present and
inner present → value.

#### 2.6.3 Optional.orElseThrow
Creates 2 EIs: empty → throws exception, present → returns value.

### 2.7 Pattern Matching (Java 16+)

#### 2.7.1 instanceof with Pattern Variable
```java
if (obj instanceof String str) {
    return str.toUpperCase();
}
```

Creates 2 EIs:
- pattern matches (variable bound)
- pattern fails

#### 2.7.2 Switch with Pattern Matching (Java 21+)
Creates N EIs (one per case including default/null cases).

## 3. Identifying Integration Points

### 3.1 Import Patterns

#### 3.1.1 Standard Imports
Standard imports do NOT create integration facts. Only the actual method calls
create integrations.

#### 3.1.2 Dynamic Class Loading
```java
Class<?> clazz = Class.forName(className);
```

This IS a boundary integration (reflection - kind: other).

### 3.2 Method Calls

#### 3.2.1 Instance Method Calls (Interunit)

##### 3.2.1.1 Source Code
```java
public void processOrder(Order order) {
    validator.validate(order);
    if (validator.isValid()) {
        orderRepository.save(order);
    }
}
```

##### 3.2.1.2 Integration Fact Analysis
Two integrations: `validate()` is unconditional, `save()` is conditional.

##### 3.2.1.3 Execution Paths
```yaml
executionPaths:
  # validate() called after entry
  - [C001M029E0001, C001M029E0002]
  
  # save() only if validation passes
  - [C001M029E0001, C001M029E0002, C001M029E0003, C001M029E0004]
```

#### 3.2.2 Static Method Calls
[Same pattern - kind: call, target includes class name]

#### 3.2.3 Constructor Calls
[Same pattern - kind: construct, target: ClassName.<init>]

### 3.3 Standard Library Boundaries

#### 3.3.1 Filesystem Operations
```java
String content = Files.readString(Path.of(filename));
```

Boundary integration: kind=filesystem, operation=read

#### 3.3.2 Network Operations (HTTP Client)
```java
HttpResponse<String> response = client.send(request, 
    HttpResponse.BodyHandlers.ofString());
```

Boundary integration: kind=network, protocol=http, operation=read

#### 3.3.3 Database Operations (JDBC)
```java
try (Connection conn = dataSource.getConnection();
     PreparedStatement stmt = conn.prepareStatement(sql)) {
    ResultSet rs = stmt.executeQuery();
}
```

Multiple boundary integrations:
- `getConnection()`: kind=database, operation=connect
- `prepareStatement()`: kind=database, operation=prepare
- `executeQuery()`: kind=database, operation=query

#### 3.3.4 Environment Variables
```java
String apiKey = System.getenv("API_KEY");
```

Boundary integration: kind=env, resource="API_KEY"

#### 3.3.5 Time/Clock Operations
```java
Instant now = Instant.now();
```

Boundary integration: kind=clock, operation=read
**Test guidance:** Mock Clock or use Clock.fixed()

#### 3.3.6 Random Number Generation
```java
int value = random.nextInt(100);
```

Boundary integration: kind=randomness, operation=read
**Test guidance:** Inject Random with fixed seed

### 3.4 Framework-Specific Patterns

#### 3.4.1 Spring Framework

##### Dependency Injection
`@Autowired` itself doesn't create integration facts. The actual method calls
on injected dependencies do.

##### Annotations/Decorators
Capture in `decorators` field:
```yaml
decorators:
  - name: Transactional
    notes: 'Spring transaction management'
```

##### Spring Data Repositories
Method calls like `repository.save()` are both interunit AND boundary
integrations (boundary.kind=database).

#### 3.4.2 Jakarta EE / Java EE
[Similar patterns - capture annotations, actual method calls create integrations]

### 3.5 Reflection and Metaprogramming

#### 3.5.1 Dynamic Method Invocation
```java
Method method = clazz.getMethod(methodName, paramTypes);
Object result = method.invoke(instance, args);
```

Two boundary integrations:
- `getMethod()`: kind=other (reflection - method lookup)
- `invoke()`: kind=dispatch (dynamic invocation)

#### 3.5.2 Class Loading/Instantiation
[Similar pattern – Class.forName, getConstructor, newInstance all create
boundary integrations with kind=other]

## 4. Edge Cases and Subtleties

### 4.1 Implicit Execution

#### 4.1.1 Getter/Setter Methods
Simple getters/setters create 1 EI. If they contain logic (conditionals), count
EIs normally.

#### 4.1.2 Autoboxing/Unboxing
Compile-time transformation - doesn't create additional EIs.

#### 4.1.3 Annotations with Runtime Effects
Capture annotations in `decorators` field. The annotation itself doesn't create
EIs - framework behavior is implicit.

### 4.2 Multi-line Expressions

#### 4.2.1 Line Continuation
Anchor EI to the line where expression evaluation begins:
- Method chains: anchor to starting line
- Builder patterns: anchor to `.build()` line
- Arithmetic expressions: anchor to assignment/return line

#### 4.2.2 Chained Method Calls
```java
List<String> names = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .sorted()
    .collect(Collectors.toList());
```

Entire chain anchored to line 1. Creates 3 EIs based on stream outcomes (empty,
all filtered, some pass).

### 4.3 Short-Circuit Evaluation

#### 4.3.1 Logical AND (&&)
```java
if (user != null && user.isActive()) {
    processUser(user);
}
```

Creates 2 EIs total: conditions true, conditions false. Do NOT count each
operand separately.

#### 4.3.2 Logical OR (||)
[Same pattern – 2 EIs total, not per operand]

### 4.4 Lazy Evaluation

#### 4.4.1 Stream Operations
Intermediate operations are lazy, so don't execute until the terminal operation.
Anchor the entire pipeline to a starting line, count outcomes based on terminal
operation results.

### 4.5 Type System Interactions

#### 4.5.1 Generics and Type Erasure
Generic type parameters are compile-time only. They don't create runtime EIs.

#### 4.5.2 Null Safety and Nullable Annotations
`@Nullable` and `@NonNull` are documentation hints. They don't create EIs unless
code explicitly checks for null.

### 4.6 Lambda Expressions and Method References

#### 4.6.1 Lambda Expressions
Lambdas are NOT separate callables. They contribute EIs to the enclosing method.

#### 4.6.2 Method References
`ClassName::methodName` is syntactic sugar for lambda. Treat equivalently.

## 5. Worked Examples

### 5.1 Input Validation with Multiple Checks

#### Source Code
```java
public class UserValidator {
    public void validateUser(User user) throws ValidationException {
        if (user == null) {
            throw new ValidationException("User cannot be null");
        }
        if (user.getEmail() == null || user.getEmail().isEmpty()) {
            throw new ValidationException("Email is required");
        }
        if (!user.getEmail().contains("@")) {
            throw new ValidationException("Invalid email format");
        }
        if (user.getAge() < 18) {
            throw new ValidationException("User must be 18 or older");
        }
    }
}
```

#### Stage 1: Outcome Path Analysis
8 total outcomes: 4 conditions × 2 outcomes each (true throws, false continues).

#### Stage 2: EI ID Assignment
C001M001E0001 through C001M001E0008 (sequential).

#### Stage 3: Integration Facts
Two interunit integrations: `user.getEmail()` and `user.getAge()` with
appropriate execution paths.

#### Stages 4 & 5: Documents
Generate three-document YAML following schema. Document 3 notes that
`getEmail()` is called multiple times but counted as single integration.

### 5.2 REST Controller with Spring

#### Source Code
```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;
    
    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        if (id == null || id <= 0) {
            return ResponseEntity.badRequest().build();
        }
        Optional<User> user = userService.findById(id);
        if (user.isPresent()) {
            return ResponseEntity.ok(user.get());
        } else {
            return ResponseEntity.notFound().build();
        }
    }
}
```

#### Key Points
- Capture Spring annotations in `decorators` field
- 5 EIs total: validation check (2), service call (1), present check (2)
- One integration: `userService.findById()` with its execution path requiring a
  valid id
- Integration is both interunit AND boundary (database access)

## 6. Quick Reference

### 6.1 Construct → EI Count Mapping

| Construct                  | EI Count | Notes                                |
|----------------------------|----------|--------------------------------------|
| Simple statement           | 1        | Assignment, method call, return      |
| If/else                    | 2        | True/false                           |
| If without else            | 2        | True enters, false skips             |
| If/elif/else (N branches)  | 2N       | Each condition has true/false        |
| Ternary                    | 2        | True/false branches                  |
| For/while loop             | 2        | 0 iterations vs ≥1 iterations        |
| Do-while loop              | 2+       | Body once + condition true/false     |
| Try/catch (N handlers)     | N+1      | Success + each exception type        |
| Switch (N cases)           | N+1      | Each case + default                  |
| Stream with filter         | 3        | Empty, all filtered, some pass       |
| Optional.map               | 2        | Empty/present                        |
| Optional.flatMap           | 3        | Empty, inner empty, inner present    |

### 6.2 Common Boundary Integrations

| Pattern                    | Boundary Kind | Example                          |
|----------------------------|---------------|----------------------------------|
| File I/O                   | filesystem    | Files.readString()               |
| HTTP                       | network       | HttpClient.send()                |
| Database (JDBC)            | database      | PreparedStatement.executeQuery() |
| Database (JPA)             | database      | EntityManager.persist()          |
| Environment                | env           | System.getenv()                  |
| Time                       | clock         | Instant.now()                    |
| Random                     | randomness    | Random.nextInt()                 |
| Subprocess                 | subprocess    | ProcessBuilder.start()           |
| Reflection                 | other         | Method.invoke()                  |

### 6.3 Integration Kind Mapping

| Java Pattern               | Integration Kind |
|----------------------------|------------------|
| Method call                | call             |
| Constructor                | construct        |
| Class.forName()            | import           |
| Method.invoke()            | dispatch         |
| File I/O                   | io               |

### 6.4 Common Pitfalls

1. ❌ Counting each condition in `&&` or `||` separately → Count as 2 EIs total
2. ❌ Creating separate callables for lambdas → Contribute to enclosing method
3. ❌ Treating imports as integrations → Only method calls create integrations
4. ❌ Each line in a multi-line chain gets EI → Anchor to the starting line
5. ❌ Ignoring try-with-resources creation → Creates 2 EIs
6. ❌ Treating annotations as EIs → Capture in decorators, don't create EIs

## Conclusion

This Java companion guide provides the patterns needed to apply the Unit Ledger
Generation Procedure to Java codebases. Key Java-specific reminders:

1. **Checked exceptions** affect control flow explicitly
2. **Type erasure** means generics don't create runtime EIs
3. **Short-circuit evaluation** counts as 2 outcomes total
4. **Stream operations** anchor to the starting line
5. **Lambdas** contribute to enclosing method, not separate callables
6. **Annotations** go in the decorators field
7. **Framework integrations** require attention to actual method calls vs.
   configuration

For questions or edge cases not covered here, refer back to the core Unit
Ledger specification and apply the principles systematically.
