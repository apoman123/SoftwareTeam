"""Tests for workspace filesystem helpers (listing excludes installed deps / caches)."""

from software_team.skills.common import filesystem


def test_list_tree_excludes_dependency_and_cache_dirs(tmp_path):
    filesystem.write_file(str(tmp_path), "app/main.py", "x = 1\n")
    filesystem.write_file(str(tmp_path), "README.md", "# project\n")
    # Installed dependency trees the test gate / toolchains create — never project source.
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "dep.py").write_text("import this\n", encoding="utf-8")
    (tmp_path / "frontend" / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "frontend" / "node_modules" / "pkg" / "index.js").write_text(
        "//\n", encoding="utf-8"
    )
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_text("", encoding="utf-8")

    tree = filesystem.list_tree(str(tmp_path))

    assert "app/main.py" in tree
    assert "README.md" in tree
    # No installed dependency or cache files leak into the listing (so an incremental run
    # never ingests `.venv` / `node_modules` as if it were the team's own code).
    assert not any(
        part in {".venv", "node_modules", "__pycache__"}
        for path in tree
        for part in path.split("/")
    )
