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

### 2026-10-05 — New tests are written in English

The surrounding tests and comments are in French; the user's rule says every file is written in
English, so new tests, comments and this file follow the rule and not the local habit.
