# Decisions

Decisions taken without validating them with the user, so they can be challenged later.

### 2026-10-05 — Fix the two reported bugs in the fork only

The user asked to fix upstream issues Mibayy/token-savior#119 and #120 "in my fork only". They
were mirrored as issues #1 and #2 on `vantaingo/token-savior` (body = upstream text plus a
"Mirrors …" line), one branch and one pull request per issue, all targeting the fork's `main`.
Nothing is pushed to, commented on, or opened against upstream. `gh` defaults to the parent
repository for a fork, so every `gh` call passes `--repo vantaingo/token-savior` explicitly.
Why: keeps the commits `[#<n>]`-prefixed against a tracker the user controls, and leaves the
decision to propose the fixes upstream to the user.

### 2026-10-05 — C# Allman fix: widen the regex terminator, nothing else

The fix is the one suggested in the issue (accept end of line after the declaration), plus an
optional trailing `// comment`, because `public class Foo // note` followed by `{` would otherwise
still be missed. `_find_type_end` and `_handle_csharp_type` already handle a brace on a following
line, so no other code changed. Positional records spanning several lines and properties are
left out: the issue itself lists them as out of scope, and each needs its own design.
Risk accepted: a type keyword at the end of a line (for example a wrapped line that ends in
`class Foo`) now matches. In practice a bare declaration with no `{` on the next line only occurs
in code that does not compile.

### 2026-10-05 — Scratch files: `/tmp/` ignored in `.gitignore`

The global rule puts scratch files in `./tmp` and requires it to be gitignored; the repository
only ignored `*.tmp`. Added `/tmp/` to `.gitignore`.

### 2026-10-05 — Schema fix: enforce aliased required arguments at dispatch, not in the schema

Issue #2 (upstream #120) suggests dropping `required` for aliased arguments and enforcing it after
`_normalize_arguments()`. Followed as suggested. The enforcement needed no new code:
`_dispatch_tool` already turns the handler's `KeyError` into an explicit error naming the argument
(`_message_argument_obligatoire`, which reads the raw `TOOL_SCHEMAS`, not the advertised schema).
The cost is that the SDK no longer rejects a call with no argument at all: the server answers with
its own error text instead, a trade accepted because a top-level `anyOf` makes the tool invisible
to Anthropic clients. A test per affected tool locks the error text.

### 2026-10-05 — Scope added to #2: `ts_search` aliases and the duplicated alias table

Two things found while tracing the fix, included because they sit on the same code path:
- `ts_search` is routed to `_handle_ts_search` before `_dispatch_tool`, so its aliases
  (`pattern`, `q`) were never normalized and a missing `query` silently searched for `""`. Since
  `ts_search` is the tool the fix makes visible again, it now normalizes and reports a missing
  `query` itself.
- `_ARG_ALIASES` / `_normalize_arguments` were defined twice in `server.py` (schemas used the
  first copy, dispatch the second, which alone had `find_symbol(query=...)`). Kept the first
  copy with the `find_symbol` entry merged in, deleted the second, so schema and dispatch can no
  longer drift apart.

### 2026-10-05 — The second pull request is stacked on the first

Both fixes append to `docs/decisions.md`, which the first branch creates, and both touch
`.gitignore`. Branch `fix/2-…` is therefore based on `fix/1-…` to avoid add/add conflicts. Merge
the first pull request first; the second then shows only its own commits.

### 2026-10-05 — New tests are written in English

The surrounding tests and comments are in French; the user's rule says every file is written in
English, so new tests, comments and this file follow the rule and not the local habit.
