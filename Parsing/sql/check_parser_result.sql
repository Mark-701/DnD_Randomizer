-- Проверка источника PH14
SELECT id, name, code FROM sources WHERE code = 'PH14';

-- Количество записей по основным таблицам
SELECT 'races' AS table_name, COUNT(*) FROM races
UNION ALL SELECT 'subraces', COUNT(*) FROM subraces
UNION ALL SELECT 'race_ability_bonuses', COUNT(*) FROM race_ability_bonuses
UNION ALL SELECT 'race_languages', COUNT(*) FROM race_languages
UNION ALL SELECT 'classes', COUNT(*) FROM classes
UNION ALL SELECT 'class_skill_choices', COUNT(*) FROM class_skill_choices
UNION ALL SELECT 'subclasses', COUNT(*) FROM subclasses
UNION ALL SELECT 'backgrounds', COUNT(*) FROM backgrounds
UNION ALL SELECT 'background_skills', COUNT(*) FROM background_skills
UNION ALL SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'spells', COUNT(*) FROM spells
UNION ALL SELECT 'spell_classes', COUNT(*) FROM spell_classes
UNION ALL SELECT 'feats', COUNT(*) FROM feats;

-- Расы и подрасы с бонусами характеристик
SELECT
    COALESCE(r.name, parent_r.name) AS race,
    s.name AS subrace,
    COALESCE(a.name, 'На выбор') AS ability,
    rab.bonus,
    rab.is_choice,
    rab.choice_count,
    rab.description
FROM race_ability_bonuses rab
LEFT JOIN races r ON rab.race_id = r.id
LEFT JOIN subraces s ON rab.subrace_id = s.id
LEFT JOIN races parent_r ON s.race_id = parent_r.id
LEFT JOIN ability_scores a ON rab.ability_score_id = a.id
ORDER BY COALESCE(r.name, parent_r.name), s.name, rab.is_choice, a.id;

-- Все расы, даже если у них нет бонусов
SELECT r.name AS race, s.name AS subrace
FROM races r
LEFT JOIN subraces s ON s.race_id = r.id
ORDER BY r.name, s.name;
