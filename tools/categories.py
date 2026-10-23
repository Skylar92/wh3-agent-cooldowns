"""The agent actions whose cooldowns the mod shortens, and the vanilla bundles that hold those cooldowns.

A cooldown is an effect bundle that blocks the action while it lasts. Character bundles are put on the
acting agent by the engine (action_results.actor_effect_bundle); faction bundles are applied by CA scripts.
"""

CATEGORIES = (
    "cult_khorne", "cult_nurgle", "cult_slaanesh", "cult_tzeentch",
    "undercity", "pirate_cove", "kroak", "ariel", "glottkin",
)

# Cult actions are shared by all four gods; the god comes from the agent subtype at runtime.
CULT = "cult"
CULT_GODS = {"_kho_": "cult_khorne", "_nur_": "cult_nurgle", "_sla_": "cult_slaanesh", "_tze_": "cult_tzeentch"}

DEFAULT_COOLDOWN = 1
COOLDOWN_RANGE = (0, 30, 1)

_CULT_BUNDLE = "wh3_main_bundle_agent_action_dignitary_hinder_settlement_success_actor"
_UNDERCITY_BUNDLE = "wh2_dlc12_bundle_underempire_cooldown"
_COVE_AGENT_BUNDLE = "wh_dlc11_bundle_agent_action_dignitary_hinder_settlement_success_actor"
_COVE_FACTION_BUNDLE = "wh2_dlc11_bundle_pirate_cove_created"
_KROAK_SETTLEMENT_BUNDLE = "wh2_dlc12_bundle_agent_action_kroak_hinder_settlement_success_lord_kroak_settlement"
_KROAK_WALLS_BUNDLE = "wh2_dlc12_bundle_agent_action_kroak_hinder_settlement_success_lord_kroak_walls"
_ARIEL_BUNDLE = "wh2_dlc16_bundle_agent_action_wizard_hinder_settlement_success_ariel"
_GLOTTKIN_LORD_BUNDLE = "wh3_dlc29_bundle_agent_action_all_hinder_character_success_convert_to_nurgle_actor"
_GLOTTKIN_GARRISON_BUNDLE = "wh3_dlc29_bundle_agent_action_all_hinder_settlement_success_wound_garrison_unit_actor"


# bundles: (bundle key, "character" | "faction", vanilla cooldown turns). The mod re-applies a bundle
# with the configured turns only when that is shorter, so the vanilla turns are the upper bound.
def _action(category, bundles, event="garrison"):
    return {"category": category, "event": event, "bundles": [list(b) for b in bundles]}


ACTIONS = {
    "wh3_main_agent_action_dignitary_hinder_settlement_establish_cult": _action(CULT, [(_CULT_BUNDLE, "character", 15)]),
    "wh3_main_agent_action_runesmith_hinder_settlement_establish_cult": _action(CULT, [(_CULT_BUNDLE, "character", 15)]),
    "wh2_dlc12_agent_action_dignitary_hinder_settlement_expand_underempire":
        _action("undercity", [(_UNDERCITY_BUNDLE, "faction", 10)]),
    "wh2_dlc12_agent_action_dignitary_hinder_settlement_expand_underempire_unique":
        _action("undercity", [(_UNDERCITY_BUNDLE, "faction", 10)]),
    "wh2_dlc16_agent_action_champion_hinder_settlement_expand_underempire":
        _action("undercity", [(_UNDERCITY_BUNDLE, "faction", 10)]),
    "wh2_dlc11_agent_action_dignitary_hinder_settlement_establish_pirate_cove":
        _action("pirate_cove", [(_COVE_AGENT_BUNDLE, "character", 15), (_COVE_FACTION_BUNDLE, "faction", 15)]),
    "wh2_dlc12_agent_action_wizard_hinder_settlement_kroak_settlement":
        _action("kroak", [(_KROAK_SETTLEMENT_BUNDLE, "character", 30)]),
    "wh2_dlc12_agent_action_wizard_hinder_settlement_kroak_walls_1": _action("kroak", [(_KROAK_WALLS_BUNDLE, "character", 30)]),
    "wh2_dlc12_agent_action_wizard_hinder_settlement_kroak_walls_2": _action("kroak", [(_KROAK_WALLS_BUNDLE, "character", 15)]),
    "wh2_dlc16_agent_action_wizard_hinder_settlement_ariel": _action("ariel", [(_ARIEL_BUNDLE, "character", 30)]),
}

for _agent in ("champion", "dignitary", "spy", "wizard"):
    ACTIONS[f"wh3_dlc29_agent_action_{_agent}_hinder_agent_wound_convert_to_nur_lord"] = _action(
        "glottkin", [(_GLOTTKIN_LORD_BUNDLE, "character", 6)], event="character")
    ACTIONS[f"wh3_dlc29_agent_action_{_agent}_hinder_settlement_convert_garrison_to_nur_mercenary"] = _action(
        "glottkin", [(_GLOTTKIN_GARRISON_BUNDLE, "character", 3)])


def scan_bundles():
    """Unique [bundle, target, category] over ACTIONS, sorted by bundle: what a first-load scan looks for."""
    found = {}
    for action in ACTIONS.values():
        for bundle, target, _ in action["bundles"]:
            found[(bundle, target)] = action["category"]
    return [[b, t, c] for (b, t), c in sorted(found.items())]
