import pytest
from lupa.lua51 import LuaRuntime

from test_agentcd_lua import MOCK
from tools.build import PACK_NAME, PREVIEW_NAME, build, main
from tools.packfile import read_pack

SCRIPT = "script/campaign/mod/agentcd.lua"
MCT = "script/mct/settings/agentcd.lua"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist") / PACK_NAME
    build(out)
    return read_pack(out)


def test_pack_contains_only_scripts(built):
    assert set(built) == {SCRIPT, MCT}


def test_built_scripts_have_no_placeholders(built):
    for path in (SCRIPT, MCT):
        assert "--@@" not in built[path].decode("utf-8"), path


def test_built_script_runs_in_mock(built):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(built[SCRIPT].decode("utf-8"))
    g = lua.globals()
    for f in list(g.FIRST_TICK.values()):
        f()
    events = {l.event for l in g.LISTENERS.values()}
    assert {"CharacterGarrisonTargetAction", "CharacterCharacterTargetAction", "FactionTurnStart",
            "MctFinalized"} <= events


def test_main_writes_pack_and_preview(tmp_path):
    main([], dist=tmp_path)
    assert (tmp_path / PACK_NAME).is_file()
    assert (tmp_path / PREVIEW_NAME).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert PREVIEW_NAME == PACK_NAME.replace(".pack", ".png")  # the launcher pairs them by name
