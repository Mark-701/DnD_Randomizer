-- show port
-- select * from races 
-- select * from race_ability_bonuses

-- --Вывод данных
SELECT 'sources' AS table_name, COUNT(*) AS rows_count FROM sources
UNION ALL SELECT 'ability_scores', COUNT(*) FROM ability_scores
UNION ALL SELECT 'skills', COUNT(*) FROM skills
UNION ALL SELECT 'languages', COUNT(*) FROM languages
UNION ALL SELECT 'magic_schools', COUNT(*) FROM magic_schools
UNION ALL SELECT 'races', COUNT(*) FROM races
UNION ALL SELECT 'subraces', COUNT(*) FROM subraces
UNION ALL SELECT 'race_ability_bonuses', COUNT(*) FROM race_ability_bonuses
UNION ALL SELECT 'race_languages', COUNT(*) FROM race_languages
UNION ALL SELECT 'classes', COUNT(*) FROM classes
UNION ALL SELECT 'subclasses', COUNT(*) FROM subclasses
UNION ALL SELECT 'class_skill_choices', COUNT(*) FROM class_skill_choices
UNION ALL SELECT 'backgrounds', COUNT(*) FROM backgrounds
UNION ALL SELECT 'background_skills', COUNT(*) FROM background_skills
UNION ALL SELECT 'tool_proficiencies', COUNT(*) FROM tool_proficiencies
UNION ALL SELECT 'background_tools', COUNT(*) FROM background_tools
UNION ALL SELECT 'equipment_categories', COUNT(*) FROM equipment_categories
UNION ALL SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'class_starting_equipment', COUNT(*) FROM class_starting_equipment
UNION ALL SELECT 'spells', COUNT(*) FROM spells
UNION ALL SELECT 'spell_classes', COUNT(*) FROM spell_classes
UNION ALL SELECT 'feats', COUNT(*) FROM feats
UNION ALL SELECT 'feat_ability_bonuses', COUNT(*) FROM feat_ability_bonuses
ORDER BY table_name;

--Тестовые данные
-- Тестовые данные для базы DnD Randomizer
-- Запускать после Parsing/sql/create_database.sql
-- PostgreSQL

BEGIN;

-- 1. Очистка только наполняемых данных. Справочники остаются.
DELETE FROM background_tools;
DELETE FROM background_skills;
DELETE FROM backgrounds;
DELETE FROM class_starting_equipment;
DELETE FROM spell_classes;
DELETE FROM spells;
DELETE FROM feat_ability_bonuses;
DELETE FROM feats;
DELETE FROM class_skill_choices;
DELETE FROM subclasses;
DELETE FROM classes;
DELETE FROM race_ability_bonuses;
DELETE FROM race_languages;
DELETE FROM subraces;
DELETE FROM races;
DELETE FROM equipment;

-- 2. Справочники, если база была создана не через create_database.sql.
INSERT INTO sources (name, code, description) VALUES
('Player''s Handbook 2014', 'PH14', 'Тестовый источник: Player''s Handbook 2014')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

INSERT INTO ability_scores (name, short_name, description) VALUES
('Сила', 'STR', 'Физическая мощь'),
('Ловкость', 'DEX', 'Проворство и реакция'),
('Телосложение', 'CON', 'Выносливость'),
('Интеллект', 'INT', 'Память и логика'),
('Мудрость', 'WIS', 'Внимательность и интуиция'),
('Харизма', 'CHA', 'Сила личности')
ON CONFLICT (name) DO NOTHING;

INSERT INTO magic_schools (name, description) VALUES
('Воплощение', 'Энергия и стихийный урон'),
('Вызов', 'Призыв и перемещение'),
('Иллюзия', 'Обман чувств'),
('Некромантия', 'Жизнь и смерть'),
('Ограждение', 'Защита'),
('Превращение', 'Изменение материи'),
('Прорицание', 'Получение знаний'),
('Очарование', 'Влияние на разум')
ON CONFLICT (name) DO NOTHING;

INSERT INTO languages (name, script, is_exotic) VALUES
('Общий', 'Общий', FALSE),
('Дварфский', 'Дварфский', FALSE),
('Эльфийский', 'Эльфийский', FALSE),
('Драконий', 'Драконий', TRUE),
('Орочий', 'Дварфский', FALSE),
('Инфернальный', 'Инфернальный', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO equipment_categories (name) VALUES
('Оружие'), ('Доспехи'), ('Инструменты'), ('Вьючные животные'),
('Транспорт'), ('Еда и напитки'), ('Услуги'), ('Амуниция')
ON CONFLICT (name) DO NOTHING;

INSERT INTO tool_proficiencies (name) VALUES
('Воровские инструменты'),
('Инструменты алхимика'),
('Инструменты травника'),
('Музыкальный инструмент'),
('Игровой набор')
ON CONFLICT (name) DO NOTHING;

INSERT INTO skills (name, ability_score_id, description) VALUES
('Атлетика', (SELECT id FROM ability_scores WHERE name='Сила'), 'Силовые действия'),
('Акробатика', (SELECT id FROM ability_scores WHERE name='Ловкость'), 'Баланс и трюки'),
('Скрытность', (SELECT id FROM ability_scores WHERE name='Ловкость'), 'Скрытое передвижение'),
('Магия', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Знания о магии'),
('История', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Исторические знания'),
('Восприятие', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Замечать детали'),
('Выживание', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Ориентирование и следы'),
('Убеждение', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Переговоры'),
('Обман', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Ложь и маскировка'),
('Запугивание', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Угрозы')
ON CONFLICT (name) DO NOTHING;

-- 3. Расы и подрасы.
INSERT INTO races (name, description, speed, source_id) VALUES
('Дварф', 'Тестовая запись расы PH14.', 25, (SELECT id FROM sources WHERE code='PH14')),
('Эльф', 'Тестовая запись расы PH14.', 30, (SELECT id FROM sources WHERE code='PH14')),
('Человек', 'Тестовая запись расы PH14.', 30, (SELECT id FROM sources WHERE code='PH14')),
('Полуэльф', 'Тестовая запись расы PH14 с выбором характеристик.', 30, (SELECT id FROM sources WHERE code='PH14')),
('Тифлинг', 'Тестовая запись расы PH14.', 30, (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description, speed = EXCLUDED.speed, source_id = EXCLUDED.source_id;

INSERT INTO subraces (name, description, race_id, source_id) VALUES
('Холмовой дварф', 'Тестовая подраса PH14.', (SELECT id FROM races WHERE name='Дварф'), (SELECT id FROM sources WHERE code='PH14')),
('Горный дварф', 'Тестовая подраса PH14.', (SELECT id FROM races WHERE name='Дварф'), (SELECT id FROM sources WHERE code='PH14')),
('Высший эльф', 'Тестовая подраса PH14.', (SELECT id FROM races WHERE name='Эльф'), (SELECT id FROM sources WHERE code='PH14')),
('Лесной эльф', 'Тестовая подраса PH14.', (SELECT id FROM races WHERE name='Эльф'), (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (race_id, name) DO UPDATE SET description = EXCLUDED.description, source_id = EXCLUDED.source_id;

INSERT INTO race_languages (race_id, language_id) VALUES
((SELECT id FROM races WHERE name='Дварф'), (SELECT id FROM languages WHERE name='Общий')),
((SELECT id FROM races WHERE name='Дварф'), (SELECT id FROM languages WHERE name='Дварфский')),
((SELECT id FROM races WHERE name='Эльф'), (SELECT id FROM languages WHERE name='Общий')),
((SELECT id FROM races WHERE name='Эльф'), (SELECT id FROM languages WHERE name='Эльфийский')),
((SELECT id FROM races WHERE name='Человек'), (SELECT id FROM languages WHERE name='Общий')),
((SELECT id FROM races WHERE name='Полуэльф'), (SELECT id FROM languages WHERE name='Общий')),
((SELECT id FROM races WHERE name='Полуэльф'), (SELECT id FROM languages WHERE name='Эльфийский')),
((SELECT id FROM races WHERE name='Тифлинг'), (SELECT id FROM languages WHERE name='Общий')),
((SELECT id FROM races WHERE name='Тифлинг'), (SELECT id FROM languages WHERE name='Инфернальный'))
ON CONFLICT DO NOTHING;

-- Фиксированные бонусы рас.
INSERT INTO race_ability_bonuses (race_id, subrace_id, ability_score_id, bonus, is_choice, choice_count, description) VALUES
((SELECT id FROM races WHERE name='Дварф'), NULL, (SELECT id FROM ability_scores WHERE name='Телосложение'), 2, FALSE, NULL, 'Дварф: Телосложение +2'),
((SELECT id FROM races WHERE name='Эльф'), NULL, (SELECT id FROM ability_scores WHERE name='Ловкость'), 2, FALSE, NULL, 'Эльф: Ловкость +2'),
((SELECT id FROM races WHERE name='Тифлинг'), NULL, (SELECT id FROM ability_scores WHERE name='Интеллект'), 1, FALSE, NULL, 'Тифлинг: Интеллект +1'),
((SELECT id FROM races WHERE name='Тифлинг'), NULL, (SELECT id FROM ability_scores WHERE name='Харизма'), 2, FALSE, NULL, 'Тифлинг: Харизма +2'),
((SELECT id FROM races WHERE name='Полуэльф'), NULL, (SELECT id FROM ability_scores WHERE name='Харизма'), 2, FALSE, NULL, 'Полуэльф: Харизма +2');

-- Человек: все характеристики +1.
INSERT INTO race_ability_bonuses (race_id, subrace_id, ability_score_id, bonus, is_choice, choice_count, description)
SELECT
    (SELECT id FROM races WHERE name='Человек'),
    NULL,
    a.id,
    1,
    FALSE,
    NULL,
    'Человек: все характеристики +1'
FROM ability_scores a
WHERE a.name IN ('Сила','Ловкость','Телосложение','Интеллект','Мудрость','Харизма');

-- Полуэльф: выбрать две другие характеристики +1, кроме Харизмы.
INSERT INTO race_ability_bonuses (race_id, subrace_id, ability_score_id, bonus, is_choice, choice_count, description)
SELECT
    (SELECT id FROM races WHERE name='Полуэльф'),
    NULL,
    a.id,
    1,
    TRUE,
    2,
    'Полуэльф: выбрать 2 характеристики из списка, каждая +1'
FROM ability_scores a
WHERE a.name IN ('Сила','Ловкость','Телосложение','Интеллект','Мудрость');

-- Бонусы подрас.
INSERT INTO race_ability_bonuses (race_id, subrace_id, ability_score_id, bonus, is_choice, choice_count, description) VALUES
(NULL, (SELECT s.id FROM subraces s JOIN races r ON r.id=s.race_id WHERE r.name='Дварф' AND s.name='Холмовой дварф'), (SELECT id FROM ability_scores WHERE name='Мудрость'), 1, FALSE, NULL, 'Холмовой дварф: Мудрость +1'),
(NULL, (SELECT s.id FROM subraces s JOIN races r ON r.id=s.race_id WHERE r.name='Дварф' AND s.name='Горный дварф'), (SELECT id FROM ability_scores WHERE name='Сила'), 2, FALSE, NULL, 'Горный дварф: Сила +2'),
(NULL, (SELECT s.id FROM subraces s JOIN races r ON r.id=s.race_id WHERE r.name='Эльф' AND s.name='Высший эльф'), (SELECT id FROM ability_scores WHERE name='Интеллект'), 1, FALSE, NULL, 'Высший эльф: Интеллект +1'),
(NULL, (SELECT s.id FROM subraces s JOIN races r ON r.id=s.race_id WHERE r.name='Эльф' AND s.name='Лесной эльф'), (SELECT id FROM ability_scores WHERE name='Мудрость'), 1, FALSE, NULL, 'Лесной эльф: Мудрость +1');

-- 4. Классы, навыки классов, подклассы.
INSERT INTO classes (name, description, hit_die, primary_ability_id, source_id) VALUES
('Воин', 'Тестовый боевой класс.', 'd10', (SELECT id FROM ability_scores WHERE name='Сила'), (SELECT id FROM sources WHERE code='PH14')),
('Волшебник', 'Тестовый заклинательский класс.', 'd6', (SELECT id FROM ability_scores WHERE name='Интеллект'), (SELECT id FROM sources WHERE code='PH14')),
('Плут', 'Тестовый ловкий класс.', 'd8', (SELECT id FROM ability_scores WHERE name='Ловкость'), (SELECT id FROM sources WHERE code='PH14')),
('Жрец', 'Тестовый божественный заклинатель.', 'd8', (SELECT id FROM ability_scores WHERE name='Мудрость'), (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description, hit_die=EXCLUDED.hit_die, primary_ability_id=EXCLUDED.primary_ability_id, source_id=EXCLUDED.source_id;

INSERT INTO class_skill_choices (class_id, skill_id) VALUES
((SELECT id FROM classes WHERE name='Воин'), (SELECT id FROM skills WHERE name='Атлетика')),
((SELECT id FROM classes WHERE name='Воин'), (SELECT id FROM skills WHERE name='Запугивание')),
((SELECT id FROM classes WHERE name='Волшебник'), (SELECT id FROM skills WHERE name='Магия')),
((SELECT id FROM classes WHERE name='Волшебник'), (SELECT id FROM skills WHERE name='История')),
((SELECT id FROM classes WHERE name='Плут'), (SELECT id FROM skills WHERE name='Скрытность')),
((SELECT id FROM classes WHERE name='Плут'), (SELECT id FROM skills WHERE name='Акробатика')),
((SELECT id FROM classes WHERE name='Жрец'), (SELECT id FROM skills WHERE name='Восприятие'))
ON CONFLICT DO NOTHING;

INSERT INTO subclasses (name, description, class_id, source_id) VALUES
('Чемпион', 'Тестовый архетип воина.', (SELECT id FROM classes WHERE name='Воин'), (SELECT id FROM sources WHERE code='PH14')),
('Школа Воплощения', 'Тестовая школа волшебника.', (SELECT id FROM classes WHERE name='Волшебник'), (SELECT id FROM sources WHERE code='PH14')),
('Вор', 'Тестовый архетип плута.', (SELECT id FROM classes WHERE name='Плут'), (SELECT id FROM sources WHERE code='PH14')),
('Домен Жизни', 'Тестовый домен жреца.', (SELECT id FROM classes WHERE name='Жрец'), (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (class_id, name) DO UPDATE SET description=EXCLUDED.description, source_id=EXCLUDED.source_id;

-- 5. Снаряжение и стартовое снаряжение классов.
INSERT INTO equipment (name, category_id, cost_value, cost_coin, weight, description, source_id) VALUES
('Длинный меч', (SELECT id FROM equipment_categories WHERE name='Оружие'), 15, 'gp', 3, 'Тестовое оружие.', (SELECT id FROM sources WHERE code='PH14')),
('Кинжал', (SELECT id FROM equipment_categories WHERE name='Оружие'), 2, 'gp', 1, 'Тестовое лёгкое оружие.', (SELECT id FROM sources WHERE code='PH14')),
('Кожаный доспех', (SELECT id FROM equipment_categories WHERE name='Доспехи'), 10, 'gp', 10, 'Тестовый лёгкий доспех.', (SELECT id FROM sources WHERE code='PH14')),
('Щит', (SELECT id FROM equipment_categories WHERE name='Доспехи'), 10, 'gp', 6, 'Тестовый щит.', (SELECT id FROM sources WHERE code='PH14')),
('Воровские инструменты', (SELECT id FROM equipment_categories WHERE name='Инструменты'), 25, 'gp', 1, 'Тестовый набор инструментов.', (SELECT id FROM sources WHERE code='PH14')),
('Набор путешественника', (SELECT id FROM equipment_categories WHERE name='Амуниция'), 10, 'gp', 5, 'Тестовый набор снаряжения.', (SELECT id FROM sources WHERE code='PH14')),
('Лошадь верховая', (SELECT id FROM equipment_categories WHERE name='Вьючные животные'), 75, 'gp', NULL, 'Тестовое животное.', (SELECT id FROM sources WHERE code='PH14')),
('Кружка эля', (SELECT id FROM equipment_categories WHERE name='Еда и напитки'), 4, 'cp', NULL, 'Тестовая еда или напиток.', (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET category_id=EXCLUDED.category_id, cost_value=EXCLUDED.cost_value, cost_coin=EXCLUDED.cost_coin, weight=EXCLUDED.weight, description=EXCLUDED.description, source_id=EXCLUDED.source_id;

INSERT INTO class_starting_equipment (class_id, equipment_id, quantity) VALUES
((SELECT id FROM classes WHERE name='Воин'), (SELECT id FROM equipment WHERE name='Длинный меч'), 1),
((SELECT id FROM classes WHERE name='Воин'), (SELECT id FROM equipment WHERE name='Щит'), 1),
((SELECT id FROM classes WHERE name='Волшебник'), (SELECT id FROM equipment WHERE name='Кинжал'), 1),
((SELECT id FROM classes WHERE name='Плут'), (SELECT id FROM equipment WHERE name='Кинжал'), 2),
((SELECT id FROM classes WHERE name='Плут'), (SELECT id FROM equipment WHERE name='Воровские инструменты'), 1),
((SELECT id FROM classes WHERE name='Жрец'), (SELECT id FROM equipment WHERE name='Щит'), 1)
ON CONFLICT (class_id, equipment_id) DO UPDATE SET quantity=EXCLUDED.quantity;

-- 6. Заклинания и связи с классами.
INSERT INTO spells (name, level, school_id, casting_time, range, components, material_components, duration, description, higher_levels, is_ritual, is_concentration, source_id) VALUES
('Огненный снаряд', 0, (SELECT id FROM magic_schools WHERE name='Воплощение'), '1 действие', '120 футов', 'В, С', NULL, 'Мгновенная', 'Тестовое боевое заклинание-заговор.', NULL, FALSE, FALSE, (SELECT id FROM sources WHERE code='PH14')),
('Магическая стрела', 1, (SELECT id FROM magic_schools WHERE name='Воплощение'), '1 действие', '120 футов', 'В, С', NULL, 'Мгновенная', 'Тестовое заклинание 1 уровня.', 'При использовании ячейки более высокого уровня создаёт дополнительный эффект.', FALSE, FALSE, (SELECT id FROM sources WHERE code='PH14')),
('Обнаружение магии', 1, (SELECT id FROM magic_schools WHERE name='Прорицание'), '1 действие', 'На себя', 'В, С', NULL, 'Концентрация, до 10 минут', 'Тестовое ритуальное заклинание.', NULL, TRUE, TRUE, (SELECT id FROM sources WHERE code='PH14')),
('Лечение ран', 1, (SELECT id FROM magic_schools WHERE name='Воплощение'), '1 действие', 'Касание', 'В, С', NULL, 'Мгновенная', 'Тестовое лечебное заклинание.', 'Лечение увеличивается при высокой ячейке.', FALSE, FALSE, (SELECT id FROM sources WHERE code='PH14')),
('Невидимость', 2, (SELECT id FROM magic_schools WHERE name='Иллюзия'), '1 действие', 'Касание', 'В, С, М', 'Ресница в смоле', 'Концентрация, до 1 часа', 'Тестовое заклинание невидимости.', 'Можно выбрать больше целей.', FALSE, TRUE, (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET level=EXCLUDED.level, school_id=EXCLUDED.school_id, casting_time=EXCLUDED.casting_time, range=EXCLUDED.range, components=EXCLUDED.components, material_components=EXCLUDED.material_components, duration=EXCLUDED.duration, description=EXCLUDED.description, higher_levels=EXCLUDED.higher_levels, is_ritual=EXCLUDED.is_ritual, is_concentration=EXCLUDED.is_concentration, source_id=EXCLUDED.source_id;

INSERT INTO spell_classes (spell_id, class_id) VALUES
((SELECT id FROM spells WHERE name='Огненный снаряд'), (SELECT id FROM classes WHERE name='Волшебник')),
((SELECT id FROM spells WHERE name='Магическая стрела'), (SELECT id FROM classes WHERE name='Волшебник')),
((SELECT id FROM spells WHERE name='Обнаружение магии'), (SELECT id FROM classes WHERE name='Волшебник')),
((SELECT id FROM spells WHERE name='Обнаружение магии'), (SELECT id FROM classes WHERE name='Жрец')),
((SELECT id FROM spells WHERE name='Лечение ран'), (SELECT id FROM classes WHERE name='Жрец')),
((SELECT id FROM spells WHERE name='Невидимость'), (SELECT id FROM classes WHERE name='Волшебник'))
ON CONFLICT DO NOTHING;

-- 7. Черты и бонусы черт.
INSERT INTO feats (name, description, prerequisite, benefit, source_id) VALUES
('Атлет', 'Тестовая черта.', NULL, 'Даёт пример бонуса к характеристике и полезный эффект.', (SELECT id FROM sources WHERE code='PH14')),
('Наблюдательный', 'Тестовая черта.', NULL, 'Даёт пример бонуса к ментальной характеристике.', (SELECT id FROM sources WHERE code='PH14')),
('Мастер оружия', 'Тестовая черта.', NULL, 'Даёт пример боевой черты.', (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description, prerequisite=EXCLUDED.prerequisite, benefit=EXCLUDED.benefit, source_id=EXCLUDED.source_id;

INSERT INTO feat_ability_bonuses (feat_id, ability_score_id, bonus) VALUES
((SELECT id FROM feats WHERE name='Атлет'), (SELECT id FROM ability_scores WHERE name='Сила'), 1),
((SELECT id FROM feats WHERE name='Атлет'), (SELECT id FROM ability_scores WHERE name='Ловкость'), 1),
((SELECT id FROM feats WHERE name='Наблюдательный'), (SELECT id FROM ability_scores WHERE name='Интеллект'), 1),
((SELECT id FROM feats WHERE name='Наблюдательный'), (SELECT id FROM ability_scores WHERE name='Мудрость'), 1),
((SELECT id FROM feats WHERE name='Мастер оружия'), (SELECT id FROM ability_scores WHERE name='Сила'), 1);

-- 8. Предыстории, навыки и инструменты предысторий.
INSERT INTO backgrounds (name, description, feature_name, feature_description, source_id) VALUES
('Солдат', 'Тестовая предыстория.', 'Воинское звание', 'Тестовая особенность предыстории.', (SELECT id FROM sources WHERE code='PH14')),
('Преступник', 'Тестовая предыстория.', 'Криминальная связь', 'Тестовая особенность предыстории.', (SELECT id FROM sources WHERE code='PH14')),
('Мудрец', 'Тестовая предыстория.', 'Исследователь', 'Тестовая особенность предыстории.', (SELECT id FROM sources WHERE code='PH14'))
ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description, feature_name=EXCLUDED.feature_name, feature_description=EXCLUDED.feature_description, source_id=EXCLUDED.source_id;

INSERT INTO background_skills (background_id, skill_id) VALUES
((SELECT id FROM backgrounds WHERE name='Солдат'), (SELECT id FROM skills WHERE name='Атлетика')),
((SELECT id FROM backgrounds WHERE name='Солдат'), (SELECT id FROM skills WHERE name='Запугивание')),
((SELECT id FROM backgrounds WHERE name='Преступник'), (SELECT id FROM skills WHERE name='Скрытность')),
((SELECT id FROM backgrounds WHERE name='Преступник'), (SELECT id FROM skills WHERE name='Обман')),
((SELECT id FROM backgrounds WHERE name='Мудрец'), (SELECT id FROM skills WHERE name='Магия')),
((SELECT id FROM backgrounds WHERE name='Мудрец'), (SELECT id FROM skills WHERE name='История'))
ON CONFLICT DO NOTHING;

INSERT INTO background_tools (background_id, tool_id) VALUES
((SELECT id FROM backgrounds WHERE name='Солдат'), (SELECT id FROM tool_proficiencies WHERE name='Игровой набор')),
((SELECT id FROM backgrounds WHERE name='Преступник'), (SELECT id FROM tool_proficiencies WHERE name='Воровские инструменты')),
((SELECT id FROM backgrounds WHERE name='Мудрец'), (SELECT id FROM tool_proficiencies WHERE name='Инструменты алхимика'))
ON CONFLICT DO NOTHING;

COMMIT;

-- 9. Быстрая проверка заполнения.
SELECT 'sources' AS table_name, COUNT(*) AS rows_count FROM sources
UNION ALL SELECT 'ability_scores', COUNT(*) FROM ability_scores
UNION ALL SELECT 'magic_schools', COUNT(*) FROM magic_schools
UNION ALL SELECT 'languages', COUNT(*) FROM languages
UNION ALL SELECT 'races', COUNT(*) FROM races
UNION ALL SELECT 'subraces', COUNT(*) FROM subraces
UNION ALL SELECT 'race_languages', COUNT(*) FROM race_languages
UNION ALL SELECT 'race_ability_bonuses', COUNT(*) FROM race_ability_bonuses
UNION ALL SELECT 'classes', COUNT(*) FROM classes
UNION ALL SELECT 'skills', COUNT(*) FROM skills
UNION ALL SELECT 'class_skill_choices', COUNT(*) FROM class_skill_choices
UNION ALL SELECT 'subclasses', COUNT(*) FROM subclasses
UNION ALL SELECT 'equipment_categories', COUNT(*) FROM equipment_categories
UNION ALL SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'class_starting_equipment', COUNT(*) FROM class_starting_equipment
UNION ALL SELECT 'spells', COUNT(*) FROM spells
UNION ALL SELECT 'spell_classes', COUNT(*) FROM spell_classes
UNION ALL SELECT 'feats', COUNT(*) FROM feats
UNION ALL SELECT 'feat_ability_bonuses', COUNT(*) FROM feat_ability_bonuses
UNION ALL SELECT 'backgrounds', COUNT(*) FROM backgrounds
UNION ALL SELECT 'background_skills', COUNT(*) FROM background_skills
UNION ALL SELECT 'tool_proficiencies', COUNT(*) FROM tool_proficiencies
UNION ALL SELECT 'background_tools', COUNT(*) FROM background_tools
ORDER BY table_name;
