import pytest

from tools.categories import ACTIONS, CATEGORIES, CULT, CULT_GODS, scan_bundles

FACTION_BUNDLES = ("wh2_dlc12_bundle_underempire_cooldown", "wh2_dlc11_bundle_pirate_cove_created")


def test_every_action_category_is_known():
    used = set()
    for key, action in ACTIONS.items():
        assert action["category"] in CATEGORIES or action["category"] == CULT, key
        assert action["event"] in ("garrison", "character"), key
        used.add(action["category"])
    if CULT in used:
        used |= set(CULT_GODS.values())
    assert set(CATEGORIES) <= used


def test_every_category_has_an_action():
    assert set(CULT_GODS.values()) == {"cult_khorne", "cult_nurgle", "cult_slaanesh", "cult_tzeentch"}
    assert {a["category"] for a in ACTIONS.values()} == {CULT, "undercity", "pirate_cove", "kroak", "ariel", "glottkin"}


def test_scan_bundles_unique():
    pairs = [(b, t) for b, t, _ in scan_bundles()]
    assert len(pairs) == len(set(pairs))
    wanted = {(b, t) for a in ACTIONS.values() for b, t, _ in a["bundles"]}
    assert set(pairs) == wanted


def test_scan_bundles_keep_category():
    by_bundle = {b: c for b, _, c in scan_bundles()}
    assert by_bundle["wh3_main_bundle_agent_action_dignitary_hinder_settlement_success_actor"] == CULT
    assert by_bundle["wh2_dlc12_bundle_underempire_cooldown"] == "undercity"


def test_glottkin_lord_actions_use_character_event():
    for key, action in ACTIONS.items():
        expected = "character" if "hinder_agent" in key else "garrison"
        assert action["event"] == expected, key


@pytest.mark.game
def test_actions_exist_in_vanilla(vanilla):
    ids = {r[vanilla("agent_actions_tables").col("unique_id")] for r in vanilla("agent_actions_tables").rows}
    assert set(ACTIONS) <= ids, sorted(set(ACTIONS) - ids)


@pytest.mark.game
def test_character_bundles_are_actor_cooldowns(vanilla):
    actions = vanilla("agent_actions_tables")
    results = vanilla("action_results_tables")
    success = {r[actions.col("unique_id")]: r[actions.col("success")] for r in actions.rows}
    actor = {r[results.col("key")]: (r[results.col("actor_effect_bundle")], r[results.col("actor_effect_bundle_turns")])
             for r in results.rows}
    for key, action in ACTIONS.items():
        for bundle, target, turns in action["bundles"]:
            if target != "character":
                continue
            assert actor[success[key]][0] == bundle, key
            assert actor[success[key]][1] == turns > 1, key


@pytest.mark.game
def test_faction_bundles_exist(vanilla):
    bundles = vanilla("effect_bundles_tables")
    keys = {r[bundles.col("key")] for r in bundles.rows}
    assert set(FACTION_BUNDLES) <= keys
    faction = {b for a in ACTIONS.values() for b, t, _ in a["bundles"] if t == "faction"}
    assert faction == set(FACTION_BUNDLES)


def test_faction_bundle_turns_match_ca_scripts():
    """wh2_dlc12_under_empire.lua applies 10 turns (plus bonus), wh2_dlc11_vampire_coast.lua 15."""
    turns = {b: n for a in ACTIONS.values() for b, t, n in a["bundles"] if t == "faction"}
    assert turns == {"wh2_dlc12_bundle_underempire_cooldown": 10, "wh2_dlc11_bundle_pirate_cove_created": 15}
