# Decisions

Decisions taken without validating them with the user, so they can be challenged later.

### 2026-10-05 — Follow the worktree: fix the path routing first, then wire a hook

Goal (user request): each time Claude creates a worktree to work on an issue, token-savior
switches to it without any manual step. Plan: (1) fix `resolve()` so a forward-slash path hint
reaches the worktree (this change, issue #6); (2) run the MCP server from this fork's checkout,
because the released 4.21.0 has no worktree routing at all; (3) a user-level `PostToolUse` hook on
`EnterWorktree|ExitWorktree` of type `mcp_tool` calling `switch_project` with `${cwd}`.
Why a hook and not server-side roots handling: Claude Code does not document
`roots/list_changed` on `EnterWorktree`, and this server ignores that notification today.
Why `os.altsep` and not normalizing the hint first: the fix stays a one-line condition on the
branch that already existed, and `abspath` normalization was already applied right before it.

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

### 2026-10-05 — #4: C# graph from regexes, edges as candidates resolved globally

No tree-sitter grammar is wired for C# here (the annotator is regex based, unlike Java), so the
graph is built from regexes over the method bodies, with comments and string literals blanked
first. The annotator cannot see other files, so it emits *candidate* names (`Type`, `Type.Method`)
and relies on the global pass (`_resolve_java_dependency_symbols`, which runs for every language) to
drop the ones that name no project symbol. That avoids a second resolution layer; the price is that
the per-file `dependency_graph` of a `.cs` file lists names that exist nowhere (`Task`,
`Console`), which is also what the Java annotator does for unresolved receivers.

The interface -> implementation edge is not built in the annotator: the existing pass
(`_build_java_implementation_edges`, applied to every file) already matches methods by short name
through `base_classes`, and it works for C# because it keys on `cls.name`.

### 2026-10-05 — #4: ambiguous function names list candidates, they do not pick one

Point 3 of the issue suggested resolving an interface/implementation pair to the implementation
"or listing both". Listing both was chosen: preferring the implementation would hide the interface
and be wrong for abstract and base classes, and the qualified name (`Type.Method`) already
resolves. The error keeps its text and gains `candidates` and `_suggestion`.

### 2026-10-05 — #4: scope left out

Not covered, to keep the change reviewable: nested types (the annotator still skips them),
extension methods, `using static` and alias resolution, overload resolution by arity (overloads
share one graph node), lambdas and delegates, expression-bodied properties, and the holes of
interpolated strings (the string is blanked whole). Attribute names are not added as class edges
(the plan said so; dropped, they are noise on `[Obsolete]`-style attributes and no project symbol
is reached through them). `_CACHE_VERSION` is bumped to 4: cached `.cs` metadata has no graph.

### 2026-10-05 — #9: drop bare names and siblings from call-chain matching, keep the class expansion

`get_call_chain` matched targets through `_function_aliases`, whose bare `func.name` is shared by
every class that has a method of that name, and through `_get_symbol_graph_aliases`, which made a
target stand for its whole class. Both are removed for methods, in `query_api.py` only; the bare
name is kept when it is itself a node of the graph (Go keys its graph by bare names), and a
constructor still stands for its class (an edge to `T` is a `new T()`).
`_function_aliases` is left alone because `find_symbol` resolves short names through it.

Not changed, deliberately: a class reached on the way is still expanded to all its methods
(`_get_call_chain_neighbors`, and the class branch of `_resolve_graph_candidate_names`). That is
what lets `A.run -> B` continue into `B`'s methods, and the Java chains rely on it; narrowing it
changes Java results and needs its own issue. Consequence: a caller that only depends on type `B`
can still be shown reaching any method of `B`.

### 2026-10-05 — Editing tools on Windows rewrote line endings

The repository is LF. `replace_symbol_source` and Python's `write_text` both left files in CRLF
(a 7 441-line diff for a 19-line change). Normalised back to LF at the byte level before
committing; check `git diff --stat` after such edits.

### 2026-10-05 — #13: generic names in public fixtures, history left as is

The fork is public. Test fixtures and CHANGELOG lines written for #4 / #9 reused class and member
names from the private codebase where the bugs were seen; they are renamed to generic ones
(`Worker`, `IRepository`, `SqlRepository`, `Store`, `GetMaxIdAsync`, `ScanAsync`). Issue, PR and
comment texts were rewritten the same way and the user deletes the old revisions in the web UI.
Rule from now on: anything posted to a public repository is anonymized before posting. The user
chose not to rewrite `main` history: the earlier commits and the PR #8 / #10 diffs keep the old
names (a force-push would not purge `refs/pull`, only GitHub support can).
