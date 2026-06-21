-- show port
-- select * from races 
-- select * from race_ability_bonuses

-- --Вывод данных
SELECT
    r.name AS race,
    COALESCE(a.name, 'На выбор') AS ability,
    rab.bonus,
    rab.is_choice,
    rab.choice_count,
    rab.description
FROM race_ability_bonuses rab
JOIN races r ON rab.race_id = r.id
LEFT JOIN ability_scores a ON rab.ability_score_id = a.id
ORDER BY r.name, rab.is_choice;

--Тестовые данные
INSERT INTO races (name, description, speed, source_id)
VALUES
('Человек', 'Универсальная раса с гибкими возможностями развития.', 30, 1),
('Эльф', 'Долгоживущая раса, известная ловкостью и магическими традициями.', 30, 1),
('Дварф', 'Крепкая и выносливая раса, связанная с ремёслами и подземными крепостями.', 25, 1),
('Гном', 'Небольшая раса, склонная к изобретательству и магии.', 25, 1);

INSERT INTO classes (name, description, hit_die, primary_ability_id, source_id)
VALUES
('Воин', 'Мастер оружия и брони.', 'd10', 1, 1),
('Маг', 'Заклинатель, использующий силу тайной магии.', 'd6', 4, 1),
('Плут', 'Ловкий специалист по скрытности, обману и точным ударам.', 'd8', 2, 1),
('Жрец', 'Божественный заклинатель, черпающий силу от высших сил.', 'd8', 5, 1);

INSERT INTO backgrounds (name, description, feature_name, feature_description, source_id)
VALUES
('Солдат', 'Персонаж имеет военное прошлое.', 'Воинское звание', 'Персонажа могут узнавать военные организации.', 1),
('Мудрец', 'Персонаж посвятил жизнь знаниям.', 'Исследователь', 'Персонаж знает, где можно найти нужную информацию.', 1),
('Преступник', 'Персонаж связан с криминальным прошлым.', 'Криминальные связи', 'Персонаж имеет контакты в преступном мире.', 1);

-- Человек: +1 ко всем характеристикам
INSERT INTO race_ability_bonuses (race_id, ability_score_id, bonus, is_choice, choice_count, description)
VALUES
(1, 1, 1, FALSE, NULL, '+1 к Силе'),
(1, 2, 1, FALSE, NULL, '+1 к Ловкости'),
(1, 3, 1, FALSE, NULL, '+1 к Телосложению'),
(1, 4, 1, FALSE, NULL, '+1 к Интеллекту'),
(1, 5, 1, FALSE, NULL, '+1 к Мудрости'),
(1, 6, 1, FALSE, NULL, '+1 к Харизме');

-- Эльф: +2 к Ловкости
INSERT INTO race_ability_bonuses (race_id, ability_score_id, bonus, is_choice, choice_count, description)
VALUES
(2, 2, 2, FALSE, NULL, '+2 к Ловкости');

-- Дварф: +2 к Телосложению
INSERT INTO race_ability_bonuses (race_id, ability_score_id, bonus, is_choice, choice_count, description)
VALUES
(3, 3, 2, FALSE, NULL, '+2 к Телосложению');

-- Гном: +2 к Интеллекту
INSERT INTO race_ability_bonuses (race_id, ability_score_id, bonus, is_choice, choice_count, description)
VALUES
(4, 4, 2, FALSE, NULL, '+2 к Интеллекту');