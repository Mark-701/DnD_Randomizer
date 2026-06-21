SELECT r.name AS race, s.name AS subrace
FROM races r
LEFT JOIN subraces s ON s.race_id = r.id
ORDER BY r.name, s.name;

SELECT COUNT(*) AS races_count FROM races;
SELECT COUNT(*) AS subraces_count FROM subraces;
