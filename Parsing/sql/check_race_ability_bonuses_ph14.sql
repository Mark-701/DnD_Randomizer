SELECT
    COALESCE(r.name, parent_r.name) AS race,
    s.name AS subrace,
    a.name AS ability,
    rab.bonus,
    rab.is_choice,
    rab.choice_count,
    rab.description
FROM race_ability_bonuses rab
LEFT JOIN races r ON r.id = rab.race_id
LEFT JOIN subraces s ON s.id = rab.subrace_id
LEFT JOIN races parent_r ON parent_r.id = s.race_id
LEFT JOIN ability_scores a ON a.id = rab.ability_score_id
ORDER BY
    COALESCE(r.name, parent_r.name),
    s.name NULLS FIRST,
    rab.is_choice,
    a.id;
