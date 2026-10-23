from pathlib import Path

import pytest
from lupa.lua51 import LuaRuntime

from tools.categories import CATEGORIES
from tools.render import render_script

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "src/script/campaign/mod/agentcd.lua").read_text(encoding="utf-8")
MOCK = (ROOT / "tests/lua/mock_game.lua").read_text(encoding="utf-8")

CULT_ACTION = "wh3_main_agent_action_dignitary_hinder_settlement_establish_cult"


@pytest.fixture
def g():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(render_script(TEMPLATE))
    g = lua.globals()
    g.lua = lua
    return g


def set_mct(g, values, broken=False):
    """Install a get_mct() global; values maps option key -> finalized value, None means no mod."""
    g.MCT_VALUES = g.lua.table_from(values) if values is not None else None
    g.MCT_BROKEN = broken
    g.lua.execute("""
        function get_mct()
            if MCT_BROKEN then error("mct is broken") end
            return { get_mod_by_key = function(_, key)
                if key ~= "agentcd" or MCT_VALUES == nil then return nil end
                return { get_option_by_key = function(_, k)
                    local v = MCT_VALUES[k]
                    if v == nil then return nil end
                    return { get_finalized_setting = function() return v end }
                end }
            end }
        end
    """)


def cooldown(g, category):
    a = g.agentcd
    return a.cooldown_for(a, category, a.settings(a))


def test_defaults_without_mct(g):
    for category in CATEGORIES:
        assert cooldown(g, category) == 1


def test_global_applies_to_all(g):
    set_mct(g, {"global_cooldown": 0})
    for category in CATEGORIES:
        assert cooldown(g, category) == 0


def test_own_value_overrides_global(g):
    set_mct(g, {"global_cooldown": 1, "own_cult_slaanesh": True, "cooldown_cult_slaanesh": 5})
    assert cooldown(g, "cult_slaanesh") == 5
    assert cooldown(g, "cult_nurgle") == 1


def test_own_value_ignored_when_unchecked(g):
    set_mct(g, {"cooldown_cult_slaanesh": 5})
    assert cooldown(g, "cult_slaanesh") == 1


def test_broken_mct_uses_defaults(g):
    set_mct(g, {}, broken=True)
    assert cooldown(g, "undercity") == 1


def test_wrong_type_mct_uses_defaults(g):
    set_mct(g, {"global_cooldown": "3"})
    assert cooldown(g, "undercity") == 1


def test_value_clamped_to_range(g):
    set_mct(g, {"global_cooldown": 99})
    assert cooldown(g, "undercity") == 30
    set_mct(g, {"global_cooldown": -4})
    assert cooldown(g, "undercity") == 0


def category(g, action, subtype):
    g.add_character(7, "f", subtype)
    a = g.agentcd
    return a.category_for(a, action, g.cm.get_character_by_cqi(g.cm, 7))


@pytest.mark.parametrize("subtype, expected", [
    ("wh3_main_sla_cultist", "cult_slaanesh"),
    ("wh3_main_pro_kho_cultist", "cult_khorne"),
    ("wh3_main_nur_cultist_plague_ritual", "cult_nurgle"),
    ("wh3_main_tze_cultist", "cult_tzeentch"),
])
def test_cult_category_by_subtype(g, subtype, expected):
    assert category(g, CULT_ACTION, subtype) == expected


def test_cult_without_god_has_no_category(g):
    assert category(g, CULT_ACTION, "some_modded_cultist") is None


def test_unknown_action_has_no_category(g):
    assert category(g, "wh2_main_agent_action_spy_hinder_agent_assassinate", "wh3_main_sla_cultist") is None


def test_plain_category(g):
    assert category(g, "wh2_dlc16_agent_action_wizard_hinder_settlement_ariel", "wh2_dlc16_wef_ariel") == "ariel"


CULT_BUNDLE = "wh3_main_bundle_agent_action_dignitary_hinder_settlement_success_actor"
UNDERCITY_ACTION = "wh2_dlc12_agent_action_dignitary_hinder_settlement_expand_underempire"
UNDERCITY_BUNDLE = "wh2_dlc12_bundle_underempire_cooldown"
COVE_ACTION = "wh2_dlc11_agent_action_dignitary_hinder_settlement_establish_pirate_cove"
COVE_AGENT_BUNDLE = "wh_dlc11_bundle_agent_action_dignitary_hinder_settlement_success_actor"
COVE_FACTION_BUNDLE = "wh2_dlc11_bundle_pirate_cove_created"
KROAK_WALLS = "wh2_dlc12_agent_action_wizard_hinder_settlement_kroak_walls_1"
KROAK_WALLS_BUNDLE = "wh2_dlc12_bundle_agent_action_kroak_hinder_settlement_success_lord_kroak_walls"
KROAK_SETTLEMENT_BUNDLE = "wh2_dlc12_bundle_agent_action_kroak_hinder_settlement_success_lord_kroak_settlement"
GLOTTKIN_LORD = "wh3_dlc29_agent_action_spy_hinder_agent_wound_convert_to_nur_lord"
GLOTTKIN_LORD_BUNDLE = "wh3_dlc29_bundle_agent_action_all_hinder_character_success_convert_to_nurgle_actor"
SLA, SKV, CST = "wh3_main_sla_seducers_of_slaanesh", "wh2_main_skv_clan_mors", "wh2_dlc11_cst_noctilus"
LZD, NUR, AI = "wh2_main_lzd_hexoatl", "wh3_dlc29_chs_host_of_the_triplets", "wh3_main_sla_rapturous_excess"


def init(g):
    for f in list(g.FIRST_TICK.values()):
        f()


def give(g, cqi, bundle):
    g.CHARACTERS[cqi].bundles[bundle] = True


def give_faction(g, key, bundle):
    g.FACTIONS[key].bundles[bundle] = True


def has(g, cqi, bundle):
    return g.CHARACTERS[cqi].bundles[bundle] is True


def faction_has(g, key, bundle):
    return g.FACTIONS[key].bundles[bundle] is True


def calls(g):
    return [list(c.values()) for c in g.CALLS.values()]


def act(g, cqi, action, bundles=(), faction_bundles=(), event="CharacterGarrisonTargetAction", result="success"):
    """The engine and CA put the cooldown bundles on, then the event fires."""
    faction = g.CHARACTERS[cqi].faction
    for b in bundles:
        give(g, cqi, b)
    for b in faction_bundles:
        give_faction(g, faction, b)
    g.fire(event, g.action_context(cqi, action, result))


def turn_start(g, turn, faction):
    g.TURN = turn
    g.fire("FactionTurnStart", g.faction_context(faction))


@pytest.fixture
def world(g):
    for key, human in ((SLA, True), (SKV, True), (CST, True), (LZD, True), (NUR, True), (AI, False)):
        g.add_faction(key, human)
    g.add_character(1, SLA, "wh3_main_sla_cultist")
    g.add_character(2, SKV, "wh2_main_skv_warlock_engineer")
    g.add_character(3, CST, "wh2_dlc11_cst_fleet_captain_deep")
    g.add_character(4, LZD, "wh2_dlc12_lzd_lord_kroak")
    g.add_character(5, NUR, "wh3_dlc29_chs_exalted_hero_mnur")
    g.add_character(6, AI, "wh3_main_sla_cultist")
    g.TURN = 5
    init(g)
    return g


def test_cult_removed_after_one_turn(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    assert has(world, 1, CULT_BUNDLE)
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_critical_success_counts(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE], result="critical")
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_zero_removes_same_turn(world):
    set_mct(world, {"global_cooldown": 0})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    assert has(world, 1, CULT_BUNDLE)
    world.run_callbacks()
    assert not has(world, 1, CULT_BUNDLE)


def test_undercity_removes_faction_bundle(world):
    set_mct(world, {"own_undercity": True, "cooldown_undercity": 2})
    act(world, 2, UNDERCITY_ACTION, faction_bundles=[UNDERCITY_BUNDLE])
    turn_start(world, 6, SKV)
    assert faction_has(world, SKV, UNDERCITY_BUNDLE)
    turn_start(world, 7, SKV)
    assert not faction_has(world, SKV, UNDERCITY_BUNDLE)
    assert ["remove_effect_bundle", UNDERCITY_BUNDLE, SKV] in calls(world)


def test_pirate_cove_removes_both_bundles(world):
    act(world, 3, COVE_ACTION, [COVE_AGENT_BUNDLE], [COVE_FACTION_BUNDLE])
    turn_start(world, 6, CST)
    assert not has(world, 3, COVE_AGENT_BUNDLE)
    assert not faction_has(world, CST, COVE_FACTION_BUNDLE)


def test_kroak_walls_only_removes_walls_bundle(world):
    give(world, 4, KROAK_SETTLEMENT_BUNDLE)
    act(world, 4, KROAK_WALLS, [KROAK_WALLS_BUNDLE])
    turn_start(world, 6, LZD)
    assert not has(world, 4, KROAK_WALLS_BUNDLE)
    assert has(world, 4, KROAK_SETTLEMENT_BUNDLE)


def test_glottkin_character_event(world):
    act(world, 5, GLOTTKIN_LORD, [GLOTTKIN_LORD_BUNDLE], event="CharacterCharacterTargetAction")
    turn_start(world, 6, NUR)
    assert not has(world, 5, GLOTTKIN_LORD_BUNDLE)


def test_glottkin_lord_action_ignored_on_garrison_event(world):
    act(world, 5, GLOTTKIN_LORD, [GLOTTKIN_LORD_BUNDLE], event="CharacterGarrisonTargetAction")
    turn_start(world, 6, NUR)
    assert has(world, 5, GLOTTKIN_LORD_BUNDLE)


def test_ai_action_ignored(world):
    act(world, 6, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    turn_start(world, 6, AI)
    assert has(world, 6, CULT_BUNDLE)


def test_failed_action_ignored(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE], result="failure")
    turn_start(world, 6, SLA)
    assert has(world, 1, CULT_BUNDLE)


def test_unknown_action_ignored(world):
    act(world, 1, "wh2_main_agent_action_spy_hinder_agent_assassinate", [CULT_BUNDLE])
    turn_start(world, 6, SLA)
    assert has(world, 1, CULT_BUNDLE)


def records(g):
    return {k: dict(v.items()) for k, v in g.agentcd.persistent.records.items()}


def test_dead_character_record_dropped(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.CHARACTERS[1] = None
    turn_start(world, 6, SLA)
    assert records(world) == {}


def test_repeat_action_overwrites_record(world):
    set_mct(world, {"global_cooldown": 3})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.TURN = 7
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    assert len(records(world)) == 1
    turn_start(world, 8, SLA)
    assert has(world, 1, CULT_BUNDLE)
    turn_start(world, 10, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_bundle_already_gone_cleans_record(world):
    set_mct(world, {"global_cooldown": 30})
    act(world, 2, UNDERCITY_ACTION, faction_bundles=[UNDERCITY_BUNDLE])
    world.FACTIONS[SKV].bundles[UNDERCITY_BUNDLE] = None
    turn_start(world, 15, SKV)
    assert records(world) == {}
    assert not any(c[0] == "remove_effect_bundle" for c in calls(world))


def test_bundle_applied_after_deferred_sweep_still_removed(world):
    act(world, 1, CULT_ACTION)
    world.run_callbacks()
    give(world, 1, CULT_BUNDLE)
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_zero_keeps_record_until_bundle_appears(world):
    set_mct(world, {"global_cooldown": 0})
    act(world, 1, CULT_ACTION)
    world.run_callbacks()
    assert not any(c[0] == "remove_effect_bundle_from_character" for c in calls(world))
    give(world, 1, CULT_BUNDLE)
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_mct_change_applies_to_running_cooldowns(world):
    set_mct(world, {"global_cooldown": 10})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.TURN = 7
    world.fire("MctFinalized", None)
    assert has(world, 1, CULT_BUNDLE)
    set_mct(world, {"global_cooldown": 1})
    world.fire("MctFinalized", None)
    assert not has(world, 1, CULT_BUNDLE)


def save_load(g, stored=None):
    context = g.lua.table()
    if stored is None:
        for f in list(g.SAVE_CALLBACKS.values()):
            f(context)
    else:
        context["agentcd_state"] = stored
    for f in list(g.LOAD_CALLBACKS.values()):
        f(context)


def test_records_survive_save_and_load(world):
    set_mct(world, {"global_cooldown": 3})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    before = records(world)
    save_load(world)
    assert records(world) == before and len(before) == 1
    turn_start(world, 8, SLA)
    assert not has(world, 1, CULT_BUNDLE)


def test_load_sweeps_due_records(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    save_load(world)
    world.TURN = 6
    init(world)
    assert not has(world, 1, CULT_BUNDLE)


def test_malformed_record_does_not_stop_sweep(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.agentcd.persistent.records["bad"] = world.lua.table_from({"target": "character", "owner": 1})
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)
    assert "bad" not in records(world)


def test_character_moved_to_ai_record_dropped(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.CHARACTERS[1].faction = AI
    turn_start(world, 6, SLA)
    assert records(world) == {}


def test_garbage_save_gives_empty_state(world):
    save_load(world, stored="garbage")
    assert records(world) == {}


@pytest.fixture
def running(g):
    """A campaign on turn 20 that already has cooldowns before the mod's first tick."""
    for key, human in ((SLA, True), (SKV, True), (AI, False)):
        g.add_faction(key, human)
    g.add_character(1, SLA, "wh3_main_sla_cultist")
    g.add_character(6, AI, "wh3_main_sla_cultist")
    give(g, 1, CULT_BUNDLE)
    give(g, 6, CULT_BUNDLE)
    give_faction(g, SKV, UNDERCITY_BUNDLE)
    g.TURN = 20
    return g


def test_scan_records_existing_cooldowns(running):
    init(running)
    assert has(running, 1, CULT_BUNDLE)
    turn_start(running, 21, SLA)
    turn_start(running, 21, SKV)
    assert not has(running, 1, CULT_BUNDLE)
    assert not faction_has(running, SKV, UNDERCITY_BUNDLE)


def test_scan_zero_removes_immediately(running):
    set_mct(running, {"global_cooldown": 0})
    init(running)
    assert not has(running, 1, CULT_BUNDLE)
    assert not faction_has(running, SKV, UNDERCITY_BUNDLE)


def test_scan_ignores_ai_factions(running):
    set_mct(running, {"global_cooldown": 0})
    init(running)
    assert has(running, 6, CULT_BUNDLE)


def test_scan_runs_once(running):
    set_mct(running, {"global_cooldown": 5})
    init(running)
    assert running.agentcd.persistent.scanned is True
    save_load(running)
    running.TURN = 23
    init(running)
    assert {r["turn"] for r in records(running).values()} == {20}


def test_scan_skips_cult_without_god(running):
    running.add_character(9, SLA, "some_modded_cultist")
    give(running, 9, CULT_BUNDLE)
    init(running)
    assert all(r["owner"] != 9 for r in records(running).values())


def applied(g, name="apply_effect_bundle_to_character"):
    return [c[1:] for c in calls(g) if c[0] == name]


def test_cult_bundle_reapplied_with_setting(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    assert applied(world) == [[CULT_BUNDLE, 1, 1]]
    assert ["remove_effect_bundle_from_character", CULT_BUNDLE, 1] in calls(world)
    assert has(world, 1, CULT_BUNDLE)


def test_setting_not_shorter_than_vanilla_leaves_bundle(world):
    set_mct(world, {"global_cooldown": 15})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    assert applied(world) == []
    assert not any(c[0] == "remove_effect_bundle_from_character" for c in calls(world))


def test_undercity_uses_real_duration(world):
    set_mct(world, {"global_cooldown": 2})
    act(world, 2, UNDERCITY_ACTION, faction_bundles=[UNDERCITY_BUNDLE])
    world.FACTIONS[SKV].durations = world.lua.table_from({UNDERCITY_BUNDLE: 5})
    world.run_callbacks()
    assert applied(world, "apply_effect_bundle") == [[UNDERCITY_BUNDLE, SKV, 2]]


def test_undercity_longer_setting_than_real_duration_not_reapplied(world):
    set_mct(world, {"global_cooldown": 7})
    act(world, 2, UNDERCITY_ACTION, faction_bundles=[UNDERCITY_BUNDLE])
    world.FACTIONS[SKV].durations = world.lua.table_from({UNDERCITY_BUNDLE: 5})
    world.run_callbacks()
    assert applied(world, "apply_effect_bundle") == []


def test_reapplied_once_per_value(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    world.agentcd.sweep(world.agentcd, SLA)
    assert len(applied(world)) == 1


def test_mct_change_reapplies_remaining(world):
    set_mct(world, {"global_cooldown": 10})
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    world.TURN = 7
    set_mct(world, {"global_cooldown": 4})
    world.fire("MctFinalized", None)
    assert applied(world) == [[CULT_BUNDLE, 1, 10], [CULT_BUNDLE, 1, 2]]


def test_raising_setting_restores_at_most_vanilla(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    world.run_callbacks()
    set_mct(world, {"global_cooldown": 20})
    world.fire("MctFinalized", None)
    assert applied(world) == [[CULT_BUNDLE, 1, 1], [CULT_BUNDLE, 1, 15]]


def test_scan_character_record_not_reapplied(running):
    init(running)
    assert applied(running) == []


def test_malformed_expires_does_not_stop_sweep(world):
    act(world, 1, CULT_ACTION, [CULT_BUNDLE])
    act(world, 3, COVE_ACTION, [COVE_AGENT_BUNDLE], [COVE_FACTION_BUNDLE])
    for record in world.agentcd.persistent.records.values():
        record.expires = "broken"
    world.agentcd.sweep(world.agentcd, SLA)
    turn_start(world, 6, SLA)
    assert not has(world, 1, CULT_BUNDLE)
