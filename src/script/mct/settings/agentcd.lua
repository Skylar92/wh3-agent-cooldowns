-- MCT settings page for Agent Cooldowns. The placeholders are filled in by tools/render.py at build time.
if not get_mct then return end

local DEFAULT_COOLDOWN = {} --@@DEFAULT_COOLDOWN@@
local RANGE = {} --@@RANGE@@
local CATEGORIES = {} --@@CATEGORIES@@
local TEXTS = {} --@@TEXTS@@
local RU_PROBE = {} --@@RU_PROBE@@

local ru = common.get_localised_string(RU_PROBE[1]) == RU_PROBE[2]

local function T(key)
    local t = TEXTS[key]
    return ru and t[2] or t[1]
end

local mct = get_mct()
local mod = mct:register_mod("agentcd")
mod:set_title(T("mod_title"))
mod:set_author("Skylar92")
mod:set_description(T("mod_description"))

local function add_option(key, kind)
    local opt = mod:add_new_option(key, kind)
    opt:set_text(T(key .. "_label"))
    opt:set_tooltip_text(T(key .. "_tip"))
    return opt
end

local function add_slider(key)
    local opt = add_option(key, "slider")
    opt:slider_set_min_max(RANGE[1], RANGE[2])
    opt:slider_set_step_size(RANGE[3])
    opt:slider_set_precision(0)
    opt:set_default_value(DEFAULT_COOLDOWN)
end

mod:add_new_section("general", T("section_general"))
add_slider("global_cooldown")

mod:add_new_section("categories", T("section_categories"))
for _, category in ipairs(CATEGORIES) do
    add_option("own_" .. category, "checkbox"):set_default_value(false)
    add_slider("cooldown_" .. category)
end
