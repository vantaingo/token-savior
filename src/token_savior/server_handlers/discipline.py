"""Discipline d'écriture servie par le serveur MCP : instructions de session et prompts de revue.

Inspiré de Ponytail (DietrichGebert/ponytail, MIT) : écrire le plus petit changement complet,
mais en s'appuyant sur ce que Token Savior sait déjà du code (appelants, impact, doublons,
code mort) au lieu de relire des fichiers.

Les instructions de session sont OPTIONNELLES (TS_DISCIPLINE=1) : mesuré le 15/10/2026 sur
tsbench (28 sessions Sonnet, édition et lecture sur un vrai dépôt), elles coûtaient 3 à 4 %
de plus par session sans gain mesurable. Les prompts, eux, ne coûtent rien tant qu'on ne
les appelle pas : actifs par défaut, TS_PROMPTS=0 pour les retirer.
"""
from __future__ import annotations

import os

INSTRUCTIONS = """\
Token Savior: navigate code by symbol, and write the smallest complete change.
Before editing, get_edit_context(symbol): its callers, dependencies and tests are the scope. Finish every caller, test and fixture the change breaks; nothing beyond.
Before writing new code, stop at the first rung that holds: 1. does it need to exist; 2. already in this codebase (search_codebase with semantic=true, find_symbol); 3. standard library or platform; 4. an installed dependency; 5. one readable line; 6. only then the minimum that works.
No abstraction, option, wrapper or "for later" code nobody asked for. Deletion beats addition (find_dead_code, find_semantic_duplicates via ts_execute).
Never cut input validation at trust boundaries, error handling that prevents data loss, security or accessibility.
Logic with a branch, loop, parser, money or security leaves one small test (find_impacted_test_files).
End the reply with one line: what was skipped or not checked, and any risk.
"""

REVIEW = """\
Review the current change like the senior dev who gets paged when it breaks. Use Token Savior, not file reads.
1. get_changed_symbols (or get_git_status) to list what the change touches{target}.
2. For each changed symbol: get_change_impact and detect_breaking_changes. The bugs worth finding are often OUTSIDE the diff: a caller, a serializer, a route that still uses the old shape.
3. find_impacted_test_files: is every risky path (branch, parser, money, security) covered by a test?
4. Look for code to cut: find_semantic_duplicates and find_dead_code on the touched files.
Report each finding as: severity (must fix / should fix / nice to have), file:line, what the code does, what goes wrong, the fix, what happens if skipped. Most severe first. No finding without evidence from a tool result.
"""

AUDIT = """\
Audit the whole project{target} and rank what to fix first. Use Token Savior, not file reads.
1. Map it: get_entry_points, then how data flows from them (get_call_chain on the main paths).
2. Risk: find_hotspots (complex and often changed), find_import_cycles, analyze_config (secrets, orphan settings), detect_breaking_changes against the last release if relevant.
3. Waste: find_dead_code, find_semantic_duplicates.
4. Safety net: find_impacted_test_files on the riskiest symbols.
Rank findings as must fix / should fix / nice to have, each with file:line, the concrete failure, and the fix. End with one verdict: what to fix first.
"""

LEAN = """\
Do this task as the smallest complete change: {task}
First get_edit_context on the symbols involved to know the full scope (callers, tests, fixtures). Then take the first rung that holds: needs to exist? already in the codebase (search_codebase semantic=true)? standard library? installed dependency? one line? only then the minimum code.
Keep validation, error handling, security and accessibility. Leave one small test if there is logic. End with what you skipped and any risk.
"""

PROMPTS = {
    "review": ("Review the current change, including breakage outside the diff, with Token Savior's impact tools.",
               REVIEW, [("target", "Optional symbol, file or ref to focus on", False)]),
    "audit": ("Audit the whole project and rank what to fix first, using Token Savior's analysis tools.",
              AUDIT, [("target", "Optional subdirectory to limit the audit", False)]),
    "lean": ("Do a task as the smallest complete change, scoped by Token Savior.",
             LEAN, [("task", "What to do", True)]),
}


def instructions_enabled() -> bool:
    return os.environ.get("TS_DISCIPLINE", "0").lower() in ("1", "true", "yes", "on")


def prompts_enabled() -> bool:
    return os.environ.get("TS_PROMPTS", "1").lower() not in ("0", "false", "no", "off")


def instructions() -> str | None:
    return INSTRUCTIONS if instructions_enabled() else None


def list_prompts():
    from mcp import types as t
    if not prompts_enabled():
        return []
    return [t.Prompt(name=name, description=desc,
                     arguments=[t.PromptArgument(name=a, description=d, required=req) for a, d, req in args])
            for name, (desc, _tpl, args) in PROMPTS.items()]


def get_prompt(name: str, arguments: dict | None):
    from mcp import types as t
    if name not in PROMPTS:
        raise ValueError(f"Unknown prompt: {name}")
    desc, tpl, _args = PROMPTS[name]
    arguments = arguments or {}
    if name == "lean":
        task = (arguments.get("task") or "").strip()
        if not task:
            raise ValueError("The 'lean' prompt needs a task.")
        text = tpl.format(task=task)
    else:
        target = (arguments.get("target") or "").strip()
        text = tpl.format(target=f", focused on {target}" if target else "")
    return t.GetPromptResult(description=desc,
                             messages=[t.PromptMessage(role="user", content=t.TextContent(type="text", text=text))])
