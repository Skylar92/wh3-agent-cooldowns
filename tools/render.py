"""Render Python data into the Lua script templates."""

from tools.categories import ACTIONS, CATEGORIES, COOLDOWN_RANGE, CULT, CULT_GODS, DEFAULT_COOLDOWN, scan_bundles
from tools.texts import MCT_TEXTS, RU_PROBE

_LUA_ESCAPES = {
    ord("\\"): "\\\\", ord('"'): '\\"', ord("\n"): "\\n", ord("\r"): "\\r", 0: "\\0",
}


def lua_literal(value):
    """Render a Python value as a Lua literal: dict -> table with string keys, list -> array table."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("inf/nan is not a Lua literal")
        return repr(value)
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, str):
        escaped = value.translate(_LUA_ESCAPES)
        return '"' + escaped + '"'
    if isinstance(value, dict):
        return "{" + ", ".join("[%s] = %s" % (lua_literal(str(k)), lua_literal(v)) for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(lua_literal(v) for v in value) + "}"
    raise TypeError("cannot render %r as a Lua literal" % (value,))


def fill_placeholders(template, values):
    """Replace each `{} --@@NAME@@` in the template with the Lua literal of values[NAME]."""
    for name, value in values.items():
        placeholder = "{} --@@%s@@" % name
        if template.count(placeholder) != 1:
            raise ValueError("template must contain exactly one " + placeholder)
        template = template.replace(placeholder, lua_literal(value))
    return template


def render_script(template):
    """Fill every placeholder of the campaign script template."""
    return fill_placeholders(template, {
        "DEFAULT_COOLDOWN": DEFAULT_COOLDOWN,
        "RANGE": list(COOLDOWN_RANGE),
        "CATEGORIES": list(CATEGORIES),
        "CULT": CULT,
        "CULT_GODS": CULT_GODS,
        "ACTIONS": ACTIONS,
        "SCAN_BUNDLES": scan_bundles(),
    })


def render_mct_settings(template):
    """Fill every placeholder of the MCT settings template."""
    return fill_placeholders(template, {
        "DEFAULT_COOLDOWN": DEFAULT_COOLDOWN,
        "RANGE": list(COOLDOWN_RANGE),
        "CATEGORIES": list(CATEGORIES),
        "TEXTS": MCT_TEXTS,
        "RU_PROBE": list(RU_PROBE),
    })
