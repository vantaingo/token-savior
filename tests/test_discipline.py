"""Instructions de session et prompts de revue servis par le serveur MCP."""
import pytest

from token_savior.server_handlers import discipline


def test_instructions_courtes_et_outils_existants(monkeypatch):
    from token_savior.tool_schemas import TOOL_SCHEMAS
    monkeypatch.setenv("TS_DISCIPLINE", "1")
    texte = discipline.instructions()
    # Elles partent dans le prompt système de chaque session : rester sous ~1,5 ko.
    assert texte and len(texte) < 1500
    # Le registre complet, pas la liste du profil actif : en profil `auto`, une
    # partie de ces outils ne s'appelle que via ts_execute, ce que le texte dit.
    noms = set(TOOL_SCHEMAS)
    for outil in ("get_edit_context", "search_codebase", "find_symbol", "find_dead_code",
                  "find_semantic_duplicates", "find_impacted_test_files", "ts_execute"):
        assert outil in texte
        assert outil in noms, f"{outil} cité dans les instructions mais absent du serveur"


def test_prompts_listes_et_rendus():
    noms = {p.name for p in discipline.list_prompts()}
    assert noms == {"review", "audit", "lean"}
    r = discipline.get_prompt("review", {"target": "parse_config"})
    assert "focused on parse_config" in r.messages[0].content.text
    assert "get_change_impact" in r.messages[0].content.text
    assert "focused on" not in discipline.get_prompt("audit", {}).messages[0].content.text
    assert "ajouter un cache" in discipline.get_prompt("lean", {"task": "ajouter un cache"}).messages[0].content.text


def test_lean_sans_tache_et_prompt_inconnu():
    with pytest.raises(ValueError):
        discipline.get_prompt("lean", {})
    with pytest.raises(ValueError):
        discipline.get_prompt("inexistant", {})


def test_instructions_optionnelles_prompts_actifs_par_defaut(monkeypatch):
    monkeypatch.delenv("TS_DISCIPLINE", raising=False)
    monkeypatch.delenv("TS_PROMPTS", raising=False)
    assert discipline.instructions() is None
    assert len(discipline.list_prompts()) == 3


def test_prompts_desactivables(monkeypatch):
    monkeypatch.setenv("TS_PROMPTS", "0")
    assert discipline.list_prompts() == []
