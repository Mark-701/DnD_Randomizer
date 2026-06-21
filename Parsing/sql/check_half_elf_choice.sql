SELECT
    r.name AS race,
    a.name AS ability,
    rab.bonus,
    rab.is_choice,
    rab.choice_count
FROM race_ability_bonuses rab
JOIN races r ON r.id = rab.race_id
JOIN ability_scores a ON a.id = rab.ability_score_id
WHERE r.name = 'Полуэльф'
ORDER BY rab.is_choice, a.id;
