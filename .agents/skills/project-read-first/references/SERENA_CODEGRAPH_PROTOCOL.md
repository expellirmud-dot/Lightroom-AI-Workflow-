# Serena and CodeGraph On-Demand Protocol

This reference defines when Serena or CodeGraph materially improves a concrete
repository question. Both capabilities remain available, but neither is a
default preflight or orientation requirement.

## Default State

- Serena = `ON_DEMAND`.
- CodeGraph = `ON_DEMAND`.
- Documentation-only work and ordinary bounded implementation use targeted
  search and bounded reads without invoking either MCP when those methods are
  sufficient.
- An MCP capability that the task does not need is `NOT_REQUIRED`, not failed,
  unavailable, or unverified.

Use the smallest sufficient tool in this order for ordinary source work:

1. targeted search;
2. bounded line or file reads;
3. ordinary symbol lookup when useful;
4. Serena when semantic symbol/navigation reasoning materially helps;
5. CodeGraph when dependency/caller/callee impact reasoning materially helps.

## Serena Protocol

Use Serena only for a concrete symbol, source, or navigation question where it
materially improves correctness or efficiency.

When Serena is required:

1. Resolve the canonical project root with `git rev-parse --show-toplevel`.
2. Activate that exact root only when it is not already the established active
   project.
3. Call `get_current_config` only when active-project ambiguity materially
   affects correctness.
4. Use symbol bodies only when names/locations are insufficient.
5. Treat Serena memory as supplementary context, never authority over Git files.

Do not call `initial_instructions` repeatedly. Do not repeat `activate_project`
or `get_current_config` merely to prove availability when the same-thread
project identity is already established. Markdown authority documents are read
directly, not through Serena symbol tools.

## CodeGraph Protocol

Use CodeGraph only for a concrete dependency, caller/callee, or architecture
impact question that targeted search or ordinary symbol lookup does not answer
safely.

When CodeGraph is required:

1. Verify that the indexed repository path equals the canonical Git root.
2. Confirm index availability and relevant freshness without rebuilding or
   mutating an index during read-first unless the task authorizes it.
3. Use narrow graph queries and normally cap results to three to five relevant
   files unless the dependency question genuinely requires more.
4. Request edges or names without source bodies when bodies are unnecessary.
5. Cross-check material graph results against repository source truth.

Do not use broad graph exploration as routine orientation. Do not use
CodeGraph merely to read ordinary source.

## Conditional Blocking

`BLOCKED_SERENA` or `BLOCKED_CODEGRAPH` may be emitted only when all three
conditions hold:

1. the concrete task genuinely requires that capability;
2. the necessary question cannot be answered safely through a smaller
   authoritative method; and
3. continuing without the capability would materially risk correctness.

When a required tool is unavailable, record its status as
`REQUIRED_BUT_UNAVAILABLE` and the exact question it blocks. A mismatch matters
only after the tool is deliberately invoked for a required question.

## Same-Thread Continuity and Anti-Duplication

Once repository root, HEAD, authority, and relevant scope are established, use
delta preflight. Repeat full orientation only when HEAD, the active Work Order,
a relevant file, or project identity materially changes, or when a previously
unnecessary capability becomes necessary.

Never retrieve the same unchanged source body through multiple mechanisms
without a concrete reason. Prohibited churn includes:

- CodeGraph source dump followed by Serena body and ordinary file reads;
- Serena body read followed by a full-file read of unchanged source;
- repeated `initial_instructions`, `activate_project`, or
  `get_current_config` calls without project ambiguity.

Reread only when the file changed, prior output was incomplete, or a new
concrete question requires a different range or symbol. Stop retrieval and
implement once sufficient evidence exists.
