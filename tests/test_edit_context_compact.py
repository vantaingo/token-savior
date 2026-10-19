"""get_edit_context : voisins bornés et commentaire d'intention au-dessus de la définition."""
from token_savior.server_handlers.code_nav import _q_get_edit_context


def _qfns(lignes_fichier, nb_fonctions=40, ligne_symbole=50):
    fichier = "\n".join(lignes_fichier)

    def get_lines(file, start, end):
        return "\n".join(fichier.splitlines()[start - 1:end])

    return {
        "find_symbol": lambda name: {"name": name, "file": "a.py", "line": ligne_symbole, "type": "function"},
        "get_function_source": lambda name, max_lines=200: "def cible(): ...",
        "get_class_source": lambda name, max_lines=200: None,
        "get_dependencies": lambda name, max_results=10: [],
        "get_dependents": lambda name, max_results=10: [],
        "get_functions": lambda file_path=None, max_results=0: (
            [{"name": "cible", "lines": [ligne_symbole, ligne_symbole + 3]}]
            + [{"name": f"f{i}", "lines": [i * 10, i * 10 + 5]} for i in range(nb_fonctions)]),
        "get_classes": lambda file_path=None, max_results=0: [],
        "find_impacted_test_files": lambda symbol_names=None, max_tests=5: {"impacted_tests": []},
        "get_lines": get_lines,
    }


def test_voisins_bornes_aux_plus_proches_avec_leur_ligne():
    r = _q_get_edit_context(_qfns(["x"] * 60), {"name": "cible"})
    assert len(r["siblings"]) == 12
    assert r["siblings_total"] == 40
    # les plus proches de la ligne 50 d'abord, et la ligne n'est plus nulle
    assert r["siblings"][0] == {"name": "f5", "type": "function", "line": 50}
    assert all("line" in s for s in r["siblings"])


def test_pas_de_total_quand_la_liste_tient():
    r = _q_get_edit_context(_qfns(["x"] * 60, nb_fonctions=3), {"name": "cible"})
    assert len(r["siblings"]) == 3 and "siblings_total" not in r


def test_intention_python_au_dessus_de_la_definition():
    lignes = ["x"] * 45 + [
        "# WHY: la priorité haute s'écrit Critical même si l'écran affiche High,",
        "# ne jamais corriger d'après l'écran.",
        "@decorateur",
        "",
    ]
    lignes = lignes[:49] + ["def cible():"]
    lignes[45], lignes[46], lignes[47], lignes[48] = (
        "x", "# WHY: la priorité haute s'écrit Critical même si l'écran affiche High,",
        "# ne jamais corriger d'après l'écran.", "@decorateur")
    r = _q_get_edit_context(_qfns(lignes), {"name": "cible"})
    assert r["why"].startswith("# WHY: la priorité haute")
    assert "ne jamais corriger" in r["why"]


def test_intention_jsdoc():
    lignes = ["x"] * 45 + ["/**", " * Rend le total TTC : arrondi au centime à la fin, pas par ligne.", " */", "x"]
    lignes = lignes[:49] + ["function cible() {}"]
    lignes[48] = " */"
    lignes[47] = " * Rend le total TTC : arrondi au centime à la fin, pas par ligne."
    lignes[46] = "/**"
    r = _q_get_edit_context(_qfns(lignes), {"name": "cible"})
    assert "arrondi au centime" in r["why"]


def test_un_bandeau_de_section_n_est_pas_une_intention():
    lignes = ["x"] * 46 + ["# ----------------------", "# Tools", "# ----------------------"]
    lignes = lignes[:49] + ["def cible():"]
    r = _q_get_edit_context(_qfns(lignes), {"name": "cible"})
    assert "why" not in r


def test_resume_projet_donne_hubs_et_sous_systemes(tmp_path):
    from token_savior.project_indexer import ProjectIndexer
    from token_savior.query_api import create_project_query_functions
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "noyau.py").write_text("def base():\n    return 1\n")
    for i in range(5):
        (tmp_path / "pkg" / f"m{i}.py").write_text(f"from pkg.noyau import base\n\ndef f{i}():\n    return base()\n")
    s = create_project_query_functions(ProjectIndexer(str(tmp_path)).index())["get_project_summary"]()
    assert "Hubs (most depended-on): base (5)" in s
    assert "Subsystems" in s and "in pkg/" in s
