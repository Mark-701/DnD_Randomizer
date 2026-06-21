-- Миграция для уже созданной БД.
-- Нужна, если таблица race_ability_bonuses уже была создана старым SQL,
-- где варианты выбора хранились одной строкой с ability_score_id = NULL.

ALTER TABLE race_ability_bonuses
DROP CONSTRAINT IF EXISTS chk_ability_bonus_choice_logic;

-- Удаляем старые строки выбора без конкретной характеристики.
-- После этого нужно заново запустить python main.py races.
DELETE FROM race_ability_bonuses
WHERE is_choice = TRUE AND ability_score_id IS NULL;

ALTER TABLE race_ability_bonuses
ADD CONSTRAINT chk_ability_bonus_choice_logic CHECK (
    (
        is_choice = FALSE
        AND ability_score_id IS NOT NULL
        AND choice_count IS NULL
    )
    OR
    (
        is_choice = TRUE
        AND ability_score_id IS NOT NULL
        AND choice_count IS NOT NULL
    )
);
