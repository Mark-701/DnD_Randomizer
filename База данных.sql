-- База данных для D&D Character Generator
-- СУБД: PostgreSQL
-- Версия: только справочники (без персонажей)

-- -- Удаление всего
-- DROP TABLE IF EXISTS 
--     background_tools,
--     background_skills,
--     backgrounds,
--     class_starting_equipment,
--     class_skill_choices,
--     subclasses,
--     spell_classes,
--     spells,
--     feat_ability_bonuses,
--     feats,
--     race_ability_bonuses,
--     race_languages,
--     subraces,
--     races,
--     equipment,
--     equipment_categories,
--     magic_items,
--     item_types,
--     item_rarities,
--     tool_proficiencies,
--     skills,
--     ability_scores,
--     magic_schools,
--     languages,
--     classes,
--     sources 
-- CASCADE;

-- Источники книг/правил
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

-- Расы
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    speed INTEGER NOT NULL DEFAULT 30,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Подрасы (например, лесной эльф, горный дворф)
CREATE TABLE subraces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Языки
CREATE TABLE languages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    script VARCHAR(50),
    is_exotic BOOLEAN NOT NULL DEFAULT FALSE
);

-- Языки доступные расе (многие ко многим)
CREATE TABLE race_languages (
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    language_id INTEGER REFERENCES languages(id) ON DELETE CASCADE,
    PRIMARY KEY (race_id, language_id)
);

-- Характеристики (базовые значения)
CREATE TABLE ability_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    short_name VARCHAR(3) NOT NULL UNIQUE,
    description TEXT
);

-- Бонусы к характеристикам от расы
CREATE TABLE race_ability_bonuses (
    id SERIAL PRIMARY KEY,

    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    subrace_id INTEGER REFERENCES subraces(id) ON DELETE CASCADE,

    ability_score_id INTEGER REFERENCES ability_scores(id) ON DELETE CASCADE,

    bonus INTEGER NOT NULL DEFAULT 0,

    is_choice BOOLEAN NOT NULL DEFAULT FALSE,
    choice_count INTEGER,
    description TEXT,

    CONSTRAINT chk_race_or_subrace CHECK (
        (race_id IS NOT NULL AND subrace_id IS NULL)
        OR
        (race_id IS NULL AND subrace_id IS NOT NULL)
    ),

    CONSTRAINT chk_ability_bonus_choice_logic CHECK (
        (
            is_choice = FALSE
            AND ability_score_id IS NOT NULL
            AND choice_count IS NULL
        )
        OR
        (
            is_choice = TRUE
            AND ability_score_id IS NULL
            AND choice_count IS NOT NULL
        )
    )
);

-- Классы
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    hit_die VARCHAR(4) NOT NULL, -- d6, d8, d10, d12
    primary_ability_id INTEGER REFERENCES ability_scores(id) ON DELETE SET NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Владение навыками
CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    ability_score_id INTEGER NOT NULL REFERENCES ability_scores(id) ON DELETE CASCADE,
    description TEXT
);

-- Навыки доступные классу для выбора
CREATE TABLE class_skill_choices (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE(class_id, skill_id)
);

-- Архетипы/подклассы
CREATE TABLE subclasses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);


-- Черты (Feats)
-------------------------------------------------------
CREATE TABLE feats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    prerequisite TEXT,
    benefit TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Связь черт с бонусами к характеристикам
CREATE TABLE feat_ability_bonuses (
    id SERIAL PRIMARY KEY,
    feat_id INTEGER NOT NULL REFERENCES feats(id) ON DELETE CASCADE,
    ability_score_id INTEGER NOT NULL REFERENCES ability_scores(id) ON DELETE CASCADE,
    bonus INTEGER NOT NULL DEFAULT 1
);

-- Заклинания
----------------------------------------
CREATE TABLE magic_schools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE spells (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    level INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0 AND level <= 9),
    school_id INTEGER NOT NULL REFERENCES magic_schools(id) ON DELETE RESTRICT,
    casting_time VARCHAR(50) NOT NULL,
    range VARCHAR(50) NOT NULL,
    components VARCHAR(20) NOT NULL, -- V, S, M (verbal, somatic, material)
    material_components TEXT,
    duration VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    higher_levels TEXT,
    is_ritual BOOLEAN NOT NULL DEFAULT FALSE,
    is_concentration BOOLEAN NOT NULL DEFAULT FALSE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Классы которые могут использовать заклинание
CREATE TABLE spell_classes (
    spell_id INTEGER NOT NULL REFERENCES spells(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (spell_id, class_id)
);


-- Магические предметы
----------------------------------------
CREATE TABLE item_rarities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE item_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE magic_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    type_id INTEGER NOT NULL REFERENCES item_types(id) ON DELETE RESTRICT,
    rarity_id INTEGER NOT NULL REFERENCES item_rarities(id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    attunement_required BOOLEAN NOT NULL DEFAULT FALSE,
    attunement_requirements TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);


-- Снаряжение и обычные предметы
------------------------------------------------
CREATE TABLE equipment_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES equipment_categories(id) ON DELETE RESTRICT,
    cost_value REAL,
    cost_coin VARCHAR(3) DEFAULT 'gp', -- cp, sp, ep, gp, pp
    weight REAL, -- в фунтах
    description TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Стартовое снаряжение класса
CREATE TABLE class_starting_equipment (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1
);


-- Предыстории (Backgrounds)
-------------------------------------------------------------
CREATE TABLE backgrounds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    feature_name VARCHAR(100),
    feature_description TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

-- Навыки от предыстории
CREATE TABLE background_skills (
    background_id INTEGER NOT NULL REFERENCES backgrounds(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (background_id, skill_id)
);

-- Владение инструментами
CREATE TABLE tool_proficiencies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Инструменты от предыстории
CREATE TABLE background_tools (
    background_id INTEGER NOT NULL REFERENCES backgrounds(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES tool_proficiencies(id) ON DELETE CASCADE,
    PRIMARY KEY (background_id, tool_id)
);

-- Индексы для оптимизации
-------------------------------------------------
CREATE INDEX idx_spells_level ON spells(level);
CREATE INDEX idx_spells_school ON spells(school_id);
CREATE INDEX idx_magic_items_rarity ON magic_items(rarity_id);
CREATE INDEX idx_magic_items_type ON magic_items(type_id);
CREATE INDEX idx_equipment_category ON equipment(category_id);

-- Заполнение базовых справочников
--------------------------------------------------------------------

-- Характеристики
INSERT INTO ability_scores (name, short_name, description) VALUES
('Сила', 'STR', 'Измеряет физическую мощь'),
('Ловкость', 'DEX', 'Измеряет проворство'),
('Телосложение', 'CON', 'Измеряет выносливость'),
('Интеллект', 'INT', 'Измеряет остроту ума'),
('Мудрость', 'WIS', 'Измеряет восприятие и интуицию'),
('Харизма', 'CHA', 'Измеряет силу личности');

-- Школы магии
INSERT INTO magic_schools (name, description) VALUES
('Воплощение', 'Манипуляция энергией'),
('Вызов', 'Призыв существ и предметов'),
('Иллюзия', 'Обман чувств'),
('Некромантия', 'Манипуляция жизнью и смертью'),
('Ограждение', 'Защита и изгнание'),
('Превращение', 'Изменение свойств материи'),
('Прорицание', 'Получение информации'),
('Очарование', 'Влияние на разум');

-- Редкости предметов
INSERT INTO item_rarities (name) VALUES
('Обычный'), ('Необычный'), ('Редкий'), ('Очень редкий'), ('Легендарный'), ('Артефакт');

-- Типы предметов
INSERT INTO item_types (name) VALUES
('Оружие'), ('Доспех'), ('Кольцо'), ('Жезл'), ('Посох'), 
('Зелье'), ('Свиток'), ('Чудесный предмет'), ('Щит'), ('Амулет');

-- Категории снаряжения
INSERT INTO equipment_categories (name) VALUES
('Оружие'), ('Доспехи'), ('Инструменты'), ('Вьючные животные'), 
('Транспорт'), ('Еда и напитки'), ('Услуги'), ('Амуниция');

-- Языки
INSERT INTO languages (name, script, is_exotic) VALUES
('Общий', 'Общий', FALSE),
('Дварфский', 'Дварфский', FALSE),
('Эльфийский', 'Эльфийский', FALSE),
('Орочий', 'Дварфский', FALSE),
('Драконий', 'Драконий', TRUE),
('Гномий', 'Дварфский', FALSE),
('Полуросликов', 'Общий', FALSE),
('Инфернальный', 'Инфернальный', TRUE),
('Бездны', 'Инфернальный', TRUE),
('Сильван', 'Эльфийский', TRUE);

-- Источники
INSERT INTO sources (name, code) VALUES
('Player''s Handbook', 'PHB'),
('Dungeon Master''s Guide', 'DMG'),
('Monster Manual', 'MM'),
('Xanathar''s Guide to Everything', 'XGE'),
('Tasha''s Cauldron of Everything', 'TCE');

-- Инструменты
INSERT INTO tool_proficiencies (name) VALUES
('Инструменты алхимика'), ('Инструменты пивовара'), ('Инструменты каллиграфа'),
('Инструменты плотника'), ('Инструменты картографа'), ('Инструменты сапожника'),
('Инструменты повара'), ('Инструменты стеклодува'), ('Инструменты ювелира'),
('Инструменты кожевника'), ('Инструменты каменщика'), ('Инструменты художника'),
('Инструменты гончара'), ('Инструменты кузнеца'), ('Инструменты ткача'),
('Инструменты резчика по дереву'), ('Воровские инструменты'),
('Инструменты штурмана'), ('Инструменты травника'),
('Набор для грима');

-- Навыки
INSERT INTO skills (name, ability_score_id, description) VALUES
('Атлетика', 1, 'Прыжки, плавание, лазание'),

('Акробатика', 2, 'Равновесие, кувырки'),
('Ловкость рук', 2, 'Карманные кражи, фокусы'),
('Скрытность', 2, 'Прятаться, красться'),

('Анализ', 4, 'Поиск улик, дедукция'),
('История', 4, 'Исторические события'),
('Магия', 4, 'Заклинания, магические традиции'),
('Природа', 4, 'Растения, животные, погода'),
('Религия', 4, 'Божества, ритуалы'),

('Восприятие', 5, 'Замечать детали'),
('Выживание', 5, 'Следопытство, ориентирование'),
('Медицина', 5, 'Лечение, диагностика'),
('Проницательность', 5, 'Чтение намерений'),
('Уход за животными', 5, 'Дрессировка, успокоение'),

('Выступление', 6, 'Развлечение публики'),
('Запугивание', 6, 'Угрозы, принуждение'),
('Обман', 6, 'Ложь, маскировка'),
('Убеждение', 6, 'Дипломатия, переговоры');