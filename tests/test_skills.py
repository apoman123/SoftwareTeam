"""Tests for the filesystem + authoring skills."""

import pytest

from software_team.skills import filesystem
from software_team.skills.authoring import extract_fenced, file_blocks, parse_file_blocks


def test_file_block_roundtrip():
    files = {"app/main.py": "print('hi')", "tests/test_x.py": "def test():\n    assert True"}
    parsed = parse_file_blocks(file_blocks(files))
    assert parsed == files


def test_extract_fenced_by_language():
    text = "intro\n```yaml\nkey: value\n```\nmid\n```sql\nSELECT 1;\n```\n"
    assert extract_fenced(text, "yaml") == "key: value"
    assert extract_fenced(text, "sql") == "SELECT 1;"


def test_write_files_creates_tree(tmp_path):
    written = filesystem.write_files(str(tmp_path), {"a/b.py": "x = 1"})
    assert (tmp_path / "a" / "b.py").read_text().strip() == "x = 1"
    assert written and written[0].endswith("b.py")
    assert filesystem.list_tree(str(tmp_path)) == ["a/b.py"]


def test_write_refuses_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        filesystem.write_file(str(tmp_path), "../escape.py", "nope")
