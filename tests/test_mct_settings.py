import re
from pathlib import Path

import pytest
from lupa.lua51 import LuaRuntime

from tools.categories import CATEGORIES, COOLDOWN_RANGE, DEFAULT_COOLDOWN
from tools.render import render_mct_settings
from tools.texts import MCT_TEXTS, RU_PROBE

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "src/script/mct/settings/agentcd.lua").read_text(encoding="utf-8")
CAMPAIGN = (ROOT / "src/script/campaign/mod/agentcd.lua").read_text(encoding="utf-8")

FAKE_MCT = """
LOG = { mods = {} }
local function recorder(rec)
    local self = {}
    for _, name in ipairs({"set_text", "set_tooltip_text", "set_default_value",
                           "slider_set_min_max", "slider_set_step_size", "slider_set_precision"}) do
        self[name] = function(me, a, b)
            rec[name] = {a, b}
            return me
        end
    end
    return self
end
function get_mct()
    return { register_mod = function(_, key)
        local mod = { key = key, options = {}, order = {}, sections = {} }
        LOG.mods[key] = mod
        local current
        local m = {}
        for _, name in ipairs({"set_title", "set_author", "set_workshop_id", "set_description"}) do
            m[name] = function(me, v) mod[name] = v return me end
        end
        m.add_new_section = function(me, skey, name)
            current = skey
            mod.sections[#mod.sections + 1] = {key = skey, name = name}
            return me
        end
        m.add_new_option = function(me, okey, otype)
            local rec = {type = otype, section = current}
            mod.options[okey] = rec
            mod.order[#mod.order + 1] = okey
            return recorder(rec)
        end
        return m
    end }
end
common = { get_localised_string = function(key) return LOC[key] or "" end }
"""


def load(russian=False):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(FAKE_MCT)
    g = lua.globals()
    g.LOC = lua.table_from({RU_PROBE[0]: RU_PROBE[1]} if russian else {})
    lua.execute(render_mct_settings(TEMPLATE))
    return g.LOG.mods["agentcd"]


@pytest.fixture
def mod():
    return load()


def opt(mod, key):
    return mod.options[key]


def test_registers_agentcd(mod):
    assert mod.key == "agentcd"
    assert mod.set_author == "Skylar92"
    assert mod.set_title == MCT_TEXTS["mod_title"][0]
    assert [mod.sections[i].key for i in (1, 2)] == ["general", "categories"]


def assert_slider(o):
    assert o.type == "slider"
    assert (o.slider_set_min_max[1], o.slider_set_min_max[2], o.slider_set_step_size[1]) == COOLDOWN_RANGE
    assert o.slider_set_precision[1] == 0
    assert o.set_default_value[1] == DEFAULT_COOLDOWN


def test_global_slider(mod):
    o = opt(mod, "global_cooldown")
    assert o.section == "general"
    assert_slider(o)


def test_category_options(mod):
    for category in CATEGORIES:
        own = opt(mod, "own_" + category)
        assert own.type == "checkbox" and own.section == "categories"
        assert own.set_default_value[1] is False
        value = opt(mod, "cooldown_" + category)
        assert value.section == "categories"
        assert_slider(value)
    keys = list(mod.order.values())
    assert keys == ["global_cooldown"] + [k for c in CATEGORIES for k in ("own_" + c, "cooldown_" + c)]


def test_option_keys_match_campaign_script(mod):
    """The campaign script builds the same keys from CATEGORIES; check its literal prefixes too."""
    assert '"global_cooldown"' in CAMPAIGN
    assert '"own_" .. category' in CAMPAIGN and '"cooldown_" .. category' in CAMPAIGN


def test_texts_english_by_default(mod):
    assert opt(mod, "global_cooldown").set_text[1] == MCT_TEXTS["global_cooldown_label"][0]
    assert opt(mod, "own_cult_slaanesh").set_text[1] == MCT_TEXTS["own_cult_slaanesh_label"][0]
    assert mod.sections[2].name == MCT_TEXTS["section_categories"][0]


def test_texts_russian_when_probe_matches():
    mod = load(russian=True)
    assert mod.set_title == MCT_TEXTS["mod_title"][1]
    assert opt(mod, "cooldown_undercity").set_tooltip_text[1] == MCT_TEXTS["cooldown_undercity_tip"][1]
    assert mod.sections[1].name == MCT_TEXTS["section_general"][1]


def test_every_text_has_both_languages():
    for key, pair in MCT_TEXTS.items():
        assert len(pair) == 2 and all(isinstance(t, str) and t for t in pair), key


def test_template_uses_only_known_texts():
    used = set(re.findall(r'T\("([a-z_]+)"\)', TEMPLATE))
    assert used <= set(MCT_TEXTS)
    for category in CATEGORIES:
        for kind in ("own", "cooldown"):
            assert f"{kind}_{category}_label" in MCT_TEXTS and f"{kind}_{category}_tip" in MCT_TEXTS


def test_does_nothing_without_mct():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(render_mct_settings(TEMPLATE))
