-- Проверка количества заклинаний PH14
SELECT COUNT(*) AS spells_count FROM spells;

-- Список заклинаний по уровням
SELECT level, COUNT(*) AS count
FROM spells
GROUP BY level
ORDER BY level;

-- Список заклинаний с классами
SELECT
    sp.name AS spell,
    sp.level,
    ms.name AS school,
    string_agg(c.name, ', ' ORDER BY c.name) AS classes
FROM spells sp
LEFT JOIN magic_schools ms ON ms.id = sp.school_id
LEFT JOIN spell_classes sc ON sc.spell_id = sp.id
LEFT JOIN classes c ON c.id = sc.class_id
GROUP BY sp.id, sp.name, sp.level, ms.name
ORDER BY sp.level, sp.name;
