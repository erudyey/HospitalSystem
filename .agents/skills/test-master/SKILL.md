---
name: test-master
description: >-
  Guides test-driven development (TDD) and generates resilient, high-coverage unit, integration, and property-based test suites.
  Focuses on boundary testing, failure paths, contract invariants, and deterministic execution.
  Use when writing tests, verifying bug fixes, designing test fixtures, or improving test coverage.
---

# Test Master: Resilient Test Architecture & TDD Specification

Test Master enforces test engineering that validates system contracts, edge conditions, and error invariants while avoiding brittle tests tied to private implementation details.

## 1. Core Testing Hierarchy & Strategy

| Level | Primary Focus | Mocking Policy | Target Speed |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Pure domain logic, algorithms, state state-machines, formatters | Zero network/DB I/O. Use pure inputs/outputs. | < 5ms per test |
| **Integration Tests** | Database queries, middleware pipelines, service interactions | Use ephemeral local DBs (e.g., test containers / SQLite). Mock external third-party APIs at the network boundary. | < 200ms per test |
| **End-to-End (E2E)** | Critical user journeys, auth flows, checkout, billing | Zero internal mocks. Test full deployment environment. | Seconds |

## 2. Test Design Matrix & Boundary Checklist

Every test suite for a component must cover these five distinct quadrants:

```text
               ┌───────────────────────────────┐
               │         Happy Path            │
               │   (Standard valid inputs)     │
               └───────────────┬───────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐       ┌───────────────┐       ┌───────────────┐
│  Boundaries  │       │ Error / Fault │       │ Edge & Corner │
│  (0, 1, max, │       │  Invariants   │       │  (Timezones,  │
│  empty, null)│       │ (Timeouts/500)│       │ Unicode, NaN) │
└──────────────┘       └───────────────┘       └───────────────┘
```

### Mandatory Edge-Case Checklist
- **Collections & Strings**: Empty array/string, single element, large volume (10k items), unicode/emoji characters, trailing/leading whitespace.
- **Numbers**: `0`, `-1`, max safe integer (`2^53 - 1` / `2^31 - 1`), floating-point precision issues (`0.1 + 0.2`).
- **Time & Dates**: Leap years, daylight saving transitions, UTC offset boundaries, timezone shifts.
- **Concurrency**: Simultaneous requests, race conditions, idempotency key replays.

## 3. The AAA (Arrange-Act-Assert) Pattern

Structure every test clearly:

```typescript
test("transfers funds between accounts when balance is sufficient", async () => {
  // 1. Arrange: setup isolated initial state
  const sender = createAccount({ balance: 500 });
  const receiver = createAccount({ balance: 100 });
  const service = new TransferService();

  // 2. Act: execute the single operation under test
  const result = await service.transfer({ from: sender.id, to: receiver.id, amount: 200 });

  // 3. Assert: verify explicit contracts and side-effects
  expect(result.status).toBe("SUCCESS");
  expect(sender.balance).toBe(300);
  expect(receiver.balance).toBe(300);
});
```

## 4. Test Smell & Anti-Pattern Banned List

1. **Mocking Everything**: If you mock 5 internal dependencies to test a 10-line function, you are testing your mocks, not your code. (Use lightweight real fakes).
2. **Testing Private Methods**: Test public observable behaviors only. If a private method is so complex it requires standalone tests, extract it into its own cohesive module.
3. **Flaky Global Time**: Always inject clock dependencies or use time-freezing utilities (e.g., `vi.useFakeTimers()`) rather than real `sleep()`.
4. **Asserting Broad Boolean Flags**: `expect(isValid).toBe(true)` gives zero diagnostic value on failure. Assert specific data fields and error messages.
