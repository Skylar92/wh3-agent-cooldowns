"""The game's Lua is older than 5.1 in places: string.find's `plain` argument crashes it.

CA's own lib_core.lua keeps the plain form commented out "until we move to a later version of lua".
"""
import re
from pathlib import Path

from tools.categories import CULT_GODS

ROOT = Path(__file__).resolve().parent.parent
LUA_FILES = sorted((ROOT / "src").rglob("*.lua"))
FIND_CALL = re.compile(r"(?::find|string\.find)\(([^()]*)\)")
LUA_MAGIC = set("^$()%.[]*+-?")


def test_lua_sources_found():
    assert len(LUA_FILES) == 2


def test_no_find_with_plain_argument():
    for path in LUA_FILES:
        for match in FIND_CALL.finditer(path.read_text(encoding="utf-8")):
            args = [a for a in match.group(1).split(",") if a.strip()]
            # s:find(p) takes 1 arg, string.find(s, p) takes 2; anything more passes init/plain.
            limit = 1 if match.group(0).startswith(":") else 2
            assert len(args) <= limit, f"{path.name}: {match.group(0)}"


def test_cult_god_parts_are_literal_patterns():
    for part in CULT_GODS:
        assert not set(part) & LUA_MAGIC, part


def test_no_file_or_os_access_in_shipped_scripts():
    """The diagnostic trace wrote to a file in the game folder; the shipped mod must not."""
    for path in LUA_FILES:
        text = path.read_text(encoding="utf-8")
        assert "io." not in text and "os." not in text and "trace(" not in text, path.name
