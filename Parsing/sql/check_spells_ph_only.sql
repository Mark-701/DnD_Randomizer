SELECT COUNT(*) AS spells_count
FROM spells;

SELECT level, COUNT(*) AS count
FROM spells
GROUP BY level
ORDER BY level;

SELECT s.name, s.level, ms.name AS school, src.code AS source
FROM spells s
LEFT JOIN magic_schools ms ON ms.id = s.school_id
LEFT JOIN sources src ON src.id = s.source_id
ORDER BY s.level, s.name;
