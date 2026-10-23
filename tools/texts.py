"""MCT texts, (English, Russian). The page picks Russian when RU_PROBE resolves to its Russian text."""

RU_PROBE = ("cultures_name_wh_main_emp_empire", "Империя")

_CATEGORY_NAMES = {
    "cult_khorne": ("Khorne cults", "Культы Кхорна"),
    "cult_nurgle": ("Nurgle cults", "Культы Нургла"),
    "cult_slaanesh": ("Slaanesh cults", "Культы Слаанеш"),
    "cult_tzeentch": ("Tzeentch cults", "Культы Тзинча"),
    "undercity": ("Under-Empire", "Подимперие"),
    "pirate_cove": ("Pirate coves", "Пиратские бухты"),
    "kroak": ("Lord Kroak", "Лорд Кроак"),
    "ariel": ("Ariel", "Ариэль"),
    "glottkin": ("Glottkin (Nurgle conversions)", "Глотткины (обращение в Нургла)"),
}

MCT_TEXTS = {
    "mod_title": ("Agent Cooldowns", "Быстрая перезарядка агентов"),
    "mod_description": (
        "Shortens the cooldowns of your agent actions: Chaos cults, the Under-Empire, pirate coves, "
        "Lord Kroak, Ariel and the Glottkin. Player factions only; the AI keeps vanilla cooldowns.",
        "Сокращает перезарядку действий ваших агентов: культы Хаоса, Подимперие, пиратские бухты, "
        "Лорд Кроак, Ариэль и Глотткины. Только для фракций игрока, у ИИ перезарядка как в игре.",
    ),
    "section_general": ("General", "Общие"),
    "section_categories": ("Per action", "По действиям"),
    "global_cooldown_label": ("Cooldown, turns", "Перезарядка, ходов"),
    "global_cooldown_tip": (
        "Turns before an agent action can be used again. 0 = again on the same turn. "
        "Never longer than the game's own cooldown.",
        "Через сколько ходов действие агента можно повторить. 0 — в тот же ход. "
        "Не бывает дольше, чем перезарядка в самой игре.",
    ),
}

for _key, (_en, _ru) in _CATEGORY_NAMES.items():
    MCT_TEXTS[f"own_{_key}_label"] = (f"{_en}: own value", f"{_ru}: своё значение")
    MCT_TEXTS[f"own_{_key}_tip"] = (
        f"Use the value below for {_en.lower()} instead of the general cooldown.",
        f"Использовать для «{_ru}» значение ниже вместо общей перезарядки.",
    )
    MCT_TEXTS[f"cooldown_{_key}_label"] = (f"{_en}, turns", f"{_ru}, ходов")
    MCT_TEXTS[f"cooldown_{_key}_tip"] = (
        f"Cooldown for {_en.lower()} when its own value is on. 0 = again on the same turn.",
        f"Перезарядка для «{_ru}», когда включено своё значение. 0 — в тот же ход.",
    )
