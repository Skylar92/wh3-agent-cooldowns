-- Agent Cooldowns: shortens the player's agent action cooldowns by removing the vanilla
-- cooldown effect bundle early. The placeholders are filled in by tools/render.py at build time.
local DEFAULT_COOLDOWN = {} --@@DEFAULT_COOLDOWN@@
local RANGE = {} --@@RANGE@@
local CATEGORIES = {} --@@CATEGORIES@@
local CULT = {} --@@CULT@@
local CULT_GODS = {} --@@CULT_GODS@@
local ACTIONS = {} --@@ACTIONS@@
local SCAN_BUNDLES = {} --@@SCAN_BUNDLES@@

local MOD_KEY = "agentcd"

agentcd = {}

local function default_settings()
	local result = { global = DEFAULT_COOLDOWN, own = {}, value = {} }
	for _, category in ipairs(CATEGORIES) do
		result.own[category] = false
		result.value[category] = DEFAULT_COOLDOWN
	end
	return result
end

local function finalized(mod, key, default)
	local option = mod:get_option_by_key(key)
	if option then
		local value = option:get_finalized_setting()
		if type(value) == type(default) then
			return value
		end
	end
	return default
end

local function read_mct(result)
	local mod = get_mct():get_mod_by_key(MOD_KEY)
	if not mod then
		return
	end
	result.global = finalized(mod, "global_cooldown", result.global)
	for _, category in ipairs(CATEGORIES) do
		result.own[category] = finalized(mod, "own_" .. category, result.own[category])
		result.value[category] = finalized(mod, "cooldown_" .. category, result.value[category])
	end
end

function agentcd:settings()
	local result = default_settings()
	if type(get_mct) == "function" then
		local loaded = default_settings()
		if pcall(read_mct, loaded) then
			result = loaded
		end
	end
	return result
end

function agentcd:cooldown_for(category, settings)
	local value = settings.global
	if settings.own[category] then
		value = settings.value[category]
	end
	return math.max(RANGE[1], math.min(RANGE[2], math.floor(value)))
end

-- Cult actions are shared by the four gods; the agent's subtype says which god it serves.
function agentcd:category_for(action_key, character)
	local action = ACTIONS[action_key]
	if not action then
		return nil
	end
	if action.category ~= CULT then
		return action.category
	end
	return self:cult_god(character)
end

function agentcd:cult_god(character)
	local subtype = character:character_subtype_key()
	for part, category in pairs(CULT_GODS) do
		-- No init/plain arguments: the game's Lua crashes on string.find's plain flag.
		-- The parts have no pattern characters, so a plain pattern search is exact.
		if subtype:find(part) then
			return category
		end
	end
	return nil
end

--------------------------------------------------------------
------------------------ COOLDOWN RECORDS --------------------
--------------------------------------------------------------
local SAVE_KEY = "agentcd_state"

local function new_state()
	return { records = {}, scanned = false }
end

agentcd.persistent = new_state()

local function record_id(target, owner, bundle)
	return target .. ":" .. tostring(owner) .. ":" .. bundle
end

-- expires: the turn the vanilla cooldown would end, when known. It caps every re-apply,
-- so the mod never makes a cooldown longer than the game's own.
function agentcd:add_record(category, target, owner, bundle, turn, expires)
	self.persistent.records[record_id(target, owner, bundle)] = {
		category = category, target = target, owner = owner, bundle = bundle, turn = turn, expires = expires,
	}
end

function agentcd:record(action_key, character, turn)
	local category = self:category_for(action_key, character)
	if not category then
		return
	end
	for _, entry in ipairs(ACTIONS[action_key].bundles) do
		local bundle, target, vanilla_turns = entry[1], entry[2], entry[3]
		local owner = character:faction():name()
		local expires = nil -- a faction bundle's real length is read from the game (techs shorten it)
		if target == "character" then
			owner = character:command_queue_index()
			expires = turn + vanilla_turns
		end
		self:add_record(category, target, owner, bundle, turn, expires)
	end
end

local function alive(interface)
	return interface and not interface:is_null_interface()
end

-- Returns the interface holding the bundle when the record belongs to faction_key,
-- false when the record should be dropped, nil when it belongs to someone else.
local function holder(entry, faction_key)
	if entry.target == "faction" then
		if entry.owner ~= faction_key then
			return nil
		end
		local faction = cm:get_faction(faction_key)
		if not alive(faction) or faction:is_dead() then
			return false
		end
		return faction
	end
	local character = cm:get_character_by_cqi(entry.owner)
	if not alive(character) then
		return false
	end
	if character:faction():name() ~= faction_key then
		-- An agent that went over to the AI is no longer ours to shorten.
		if not character:faction():is_human() then
			return false
		end
		return nil
	end
	return character
end

-- Turns left on a faction's bundle, or nil when the game does not say.
local function faction_bundle_duration(faction, bundle)
	local bundles = faction:effect_bundles()
	for i = 0, bundles:num_items() - 1 do
		local item = bundles:item_at(i)
		if item:key() == bundle then
			local turns = item:duration()
			if type(turns) == "number" and turns > 0 then
				return turns
			end
			return nil
		end
	end
	return nil
end

-- Re-applies the cooldown bundle so the game shows the configured turns instead of the vanilla ones.
local function show_turns(entry, owner, faction_key, cooldown, turn)
	if type(entry.expires) ~= "number" then
		entry.expires = nil
	end
	if type(entry.applied) ~= "number" then
		entry.applied = nil
	end
	if entry.target == "faction" and not entry.expires and not entry.applied then
		local turns = faction_bundle_duration(owner, entry.bundle)
		if turns then
			entry.expires = turn + turns
		end
	end
	if not entry.expires then
		return
	end
	local wanted = math.min(entry.turn + cooldown, entry.expires)
	if wanted == (entry.applied or entry.expires) or wanted - turn <= 0 then
		return
	end
	if entry.target == "faction" then
		cm:remove_effect_bundle(entry.bundle, faction_key)
		cm:apply_effect_bundle(entry.bundle, faction_key, wanted - turn)
	else
		cm:remove_effect_bundle_from_character(entry.bundle, owner)
		cm:apply_effect_bundle_to_character(entry.bundle, owner, wanted - turn)
	end
	entry.applied = wanted
end

local function valid(entry)
	return type(entry) == "table" and type(entry.bundle) == "string" and type(entry.turn) == "number"
		and type(entry.category) == "string" and (entry.target == "faction" or entry.target == "character")
		and entry.owner ~= nil
end

function agentcd:sweep(faction_key)
	local settings = self:settings()
	local turn = cm:turn_number()
	for id, entry in pairs(self.persistent.records) do
		local owner = valid(entry) and holder(entry, faction_key)
		-- On the action's own turn the bundle may not be applied yet: keep waiting for it.
		local present = owner and owner:has_effect_bundle(entry.bundle)
		local cooldown = valid(entry) and self:cooldown_for(entry.category, settings)
		if owner == false or (owner and not present and turn > entry.turn) then
			self.persistent.records[id] = nil
		elseif present and turn < entry.turn + cooldown then
			show_turns(entry, owner, faction_key, cooldown, turn)
		elseif present then
			if entry.target == "faction" then
				cm:remove_effect_bundle(entry.bundle, faction_key)
			else
				cm:remove_effect_bundle_from_character(entry.bundle, owner)
			end
			self.persistent.records[id] = nil
		end
	end
end

function agentcd:sweep_humans()
	for _, faction_key in ipairs(cm:get_human_factions()) do
		self:sweep(faction_key)
	end
end

-- Cooldowns already running when the mod is added have no action turn: count them from now.
function agentcd:scan(turn)
	if self.persistent.scanned then
		return
	end
	for _, faction_key in ipairs(cm:get_human_factions()) do
		local faction = cm:get_faction(faction_key)
		if alive(faction) then
			for _, entry in ipairs(SCAN_BUNDLES) do
				local bundle, target, category = entry[1], entry[2], entry[3]
				if target == "faction" and faction:has_effect_bundle(bundle) then
					self:add_record(category, target, faction_key, bundle, turn)
				end
			end
			local characters = faction:character_list()
			for i = 0, characters:num_items() - 1 do
				local character = characters:item_at(i)
				for _, entry in ipairs(SCAN_BUNDLES) do
					local bundle, target, category = entry[1], entry[2], entry[3]
					if target == "character" and character:has_effect_bundle(bundle) then
						if category == CULT then
							category = self:cult_god(character)
						end
						if category then
							self:add_record(category, target, character:command_queue_index(), bundle, turn)
						end
					end
				end
			end
		end
	end
	self.persistent.scanned = true
end

--------------------------------------------------------------
--------------------------- LISTENERS ------------------------
--------------------------------------------------------------
local function action_listener(name, event, kind)
	core:add_listener(
		name,
		event,
		function(context)
			local action = ACTIONS[context:agent_action_key()]
			return action ~= nil and action.event == kind
				and (context:mission_result_success() or context:mission_result_critial_success())
				and context:character():faction():is_human()
		end,
		function(context)
			local character = context:character()
			local faction_key = character:faction():name()
			agentcd:record(context:agent_action_key(), character, cm:turn_number())
			-- Deferred so the engine and CA scripts have applied their bundle first;
			-- with a 0-turn setting this frees the action again on the same turn.
			cm:callback(function() agentcd:sweep(faction_key) end, 0.2)
		end,
		true
	)
end

function agentcd:init()
	action_listener("agentcd_garrison_action", "CharacterGarrisonTargetAction", "garrison")
	action_listener("agentcd_character_action", "CharacterCharacterTargetAction", "character")

	core:add_listener(
		"agentcd_faction_turn_start",
		"FactionTurnStart",
		function(context)
			return context:faction():is_human()
		end,
		function(context)
			agentcd:sweep(context:faction():name())
		end,
		true
	)

	core:add_listener(
		"agentcd_mct_finalized",
		"MctFinalized",
		true,
		function()
			agentcd:sweep_humans()
		end,
		true
	)

	-- Last on purpose: nothing in here may stop the listeners above from registering.
	-- The sweep also catches records that fell due while no turn-start listener ran (a load).
	self:scan(cm:turn_number())
	self:sweep_humans()
end

cm:add_first_tick_callback(
	function()
		agentcd:init()
	end
)

--------------------------------------------------------------
----------------------- SAVING / LOADING ---------------------
--------------------------------------------------------------
cm:add_saving_game_callback(
	function(context)
		cm:save_named_value(SAVE_KEY, agentcd.persistent, context)
	end
)

cm:add_loading_game_callback(
	function(context)
		local loaded = cm:load_named_value(SAVE_KEY, new_state(), context)
		local state = new_state()
		if type(loaded) == "table" then
			if type(loaded.records) == "table" then
				state.records = loaded.records
			end
			state.scanned = loaded.scanned == true
		end
		agentcd.persistent = state
	end
)
