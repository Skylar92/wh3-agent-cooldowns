-- Minimal stand-ins for the campaign API used by agentcd.lua.
-- Every cm call that changes the game is recorded in CALLS as {name, args...}.
CALLS = {}
LISTENERS = {}
FIRST_TICK = {}
SAVE_CALLBACKS = {}
LOAD_CALLBACKS = {}
CALLBACKS = {}
SAVED_VALUES = {}
TURN = 1

local function rec(...) CALLS[#CALLS + 1] = {...} end

-- FACTIONS[key] = {human = bool, dead = bool, bundles = {[key] = true}}
-- CHARACTERS[cqi] = {faction = key, subtype = key, bundles = {[key] = true}}
FACTIONS = {}
CHARACTERS = {}

local function null_interface() return { is_null_interface = function() return true end } end

local function list(items)
	return {
		num_items = function() return #items end,
		item_at = function(_, i) return items[i + 1] end,
	}
end

local make_character

function make_faction(key)
	local data = FACTIONS[key]
	if not data then return null_interface() end
	return {
		name = function() return key end,
		is_null_interface = function() return false end,
		is_human = function() return data.human == true end,
		is_dead = function() return data.dead == true end,
		has_effect_bundle = function(_, b) return (data.bundles or {})[b] == true end,
		effect_bundles = function()
			local items = {}
			for b in pairs(data.bundles or {}) do
				local d = (data.durations or {})[b] or 0
				items[#items + 1] = { key = function() return b end, duration = function() return d end }
			end
			return list(items)
		end,
		character_list = function()
			local items = {}
			local cqis = {}
			for cqi, c in pairs(CHARACTERS) do
				if c.faction == key then cqis[#cqis + 1] = cqi end
			end
			table.sort(cqis)
			for _, cqi in ipairs(cqis) do items[#items + 1] = make_character(cqi) end
			return list(items)
		end,
	}
end

make_character = function(cqi)
	local data = CHARACTERS[cqi]
	if not data then return null_interface() end
	return {
		command_queue_index = function() return cqi end,
		is_null_interface = function() return false end,
		character_subtype_key = function() return data.subtype end,
		faction = function() return make_faction(data.faction) end,
		has_effect_bundle = function(_, b) return (data.bundles or {})[b] == true end,
	}
end

function add_faction(key, human)
	FACTIONS[key] = { human = human, bundles = {} }
end

function add_character(cqi, faction, subtype)
	CHARACTERS[cqi] = { faction = faction, subtype = subtype, bundles = {} }
end

-- Lua iteration helper used by CA scripts.
function model_pairs(l)
	local i = -1
	return function()
		i = i + 1
		if i < l:num_items() then return i, l:item_at(i) end
	end
end

cm = {}
function cm:get_saved_value(k) return SAVED_VALUES[k] end
function cm:set_saved_value(k, v) SAVED_VALUES[k] = v end
function cm:turn_number() return TURN end
function cm:get_faction(key)
	if not FACTIONS[key] then return false end
	return make_faction(key)
end
function cm:get_character_by_cqi(cqi)
	if not CHARACTERS[cqi] then return false end
	return make_character(cqi)
end
function cm:get_human_factions()
	local keys = {}
	for key, f in pairs(FACTIONS) do
		if f.human then keys[#keys + 1] = key end
	end
	table.sort(keys)
	return keys
end
function cm:remove_effect_bundle(bundle, faction_key)
	rec("remove_effect_bundle", bundle, faction_key)
	if FACTIONS[faction_key] then FACTIONS[faction_key].bundles[bundle] = nil end
end
function cm:apply_effect_bundle(bundle, faction_key, turns)
	rec("apply_effect_bundle", bundle, faction_key, turns)
	FACTIONS[faction_key].bundles[bundle] = true
	FACTIONS[faction_key].durations = FACTIONS[faction_key].durations or {}
	FACTIONS[faction_key].durations[bundle] = turns
end
function cm:apply_effect_bundle_to_character(bundle, character, turns)
	local cqi = character:command_queue_index()
	rec("apply_effect_bundle_to_character", bundle, cqi, turns)
	CHARACTERS[cqi].bundles[bundle] = true
end
function cm:remove_effect_bundle_from_character(bundle, character)
	local cqi = character:command_queue_index()
	rec("remove_effect_bundle_from_character", bundle, cqi)
	if CHARACTERS[cqi] then CHARACTERS[cqi].bundles[bundle] = nil end
end
function cm:callback(f, interval) CALLBACKS[#CALLBACKS + 1] = f end
function run_callbacks()
	local queued = CALLBACKS
	CALLBACKS = {}
	for _, f in ipairs(queued) do f() end
end
function cm:add_first_tick_callback(f) FIRST_TICK[#FIRST_TICK + 1] = f end
function cm:add_saving_game_callback(f) SAVE_CALLBACKS[#SAVE_CALLBACKS + 1] = f end
function cm:add_loading_game_callback(f) LOAD_CALLBACKS[#LOAD_CALLBACKS + 1] = f end
-- Mirrors lib_campaign_manager: tables are serialised (stored as copies here) and
-- only come back when the default is a table.
local function deep_copy(v)
	if type(v) ~= "table" then return v end
	local t = {}
	for k, x in pairs(v) do t[k] = deep_copy(x) end
	return t
end
function cm:save_named_value(name, value, context) context[name] = deep_copy(value) end
function cm:load_named_value(name, default, context)
	local stored = context[name]
	if type(default) == "table" then
		if type(stored) == "table" then return deep_copy(stored) end
		return default
	end
	if stored == nil then return default end
	return stored
end

core = {}
function core:add_listener(name, event, condition, callback, persistent)
	LISTENERS[#LISTENERS + 1] = { name = name, event = event, condition = condition, callback = callback }
end

function fire(event, context)
	for _, l in ipairs(LISTENERS) do
		if l.event == event and (l.condition == true or l.condition(context)) then l.callback(context) end
	end
end

-- Context for CharacterGarrisonTargetAction / CharacterCharacterTargetAction.
function action_context(cqi, action_key, result)
	result = result or "success"
	return {
		character = function() return make_character(cqi) end,
		agent_action_key = function() return action_key end,
		mission_result_success = function() return result == "success" end,
		mission_result_critial_success = function() return result == "critical" end,
	}
end

function faction_context(key)
	return { faction = function() return make_faction(key) end }
end

OUT = {}
function out(s) OUT[#OUT + 1] = s end
