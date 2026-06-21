SELECT 'spells' AS table_name, COUNT(*) AS count FROM spells
UNION ALL
SELECT 'feats' AS table_name, COUNT(*) AS count FROM feats
UNION ALL
SELECT 'spell_classes' AS table_name, COUNT(*) AS count FROM spell_classes
UNION ALL
SELECT 'feat_ability_bonuses' AS table_name, COUNT(*) AS count FROM feat_ability_bonuses;

SELECT s.name, s.level, ms.name AS school
FROM spells s
JOIN magic_schools ms ON ms.id = s.school_id
ORDER BY s.level, s.name;

SELECT f.name, f.prerequisite
FROM feats f
ORDER BY f.name;
