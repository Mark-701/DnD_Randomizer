-- База данных для D&D Randomizer
-- PostgreSQL
-- Полная пересборка справочников под парсер PH14.
-- ВАЖНО: этот файл удаляет старые таблицы и создаёт их заново.

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

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE ability_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    short_name VARCHAR(3) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE magic_schools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE languages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    script VARCHAR(50),
    is_exotic BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    speed INTEGER NOT NULL DEFAULT 30,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE subraces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    UNIQUE (race_id, name)
);

CREATE TABLE race_languages (
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    PRIMARY KEY (race_id, language_id)
);

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
            -- Вариант выбора тоже хранит ability_score_id.
            -- Так в БД видно ВСЕ характеристики, из которых можно выбирать.
            -- Например, полуэльф PH14: Сила/Ловкость/Телосложение/Интеллект/Мудрость +1, выбрать 2.
            is_choice = TRUE
            AND ability_score_id IS NOT NULL
            AND choice_count IS NOT NULL
        )
    )
);

CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    hit_die VARCHAR(4) NOT NULL,
    primary_ability_id INTEGER REFERENCES ability_scores(id) ON DELETE SET NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    ability_score_id INTEGER NOT NULL REFERENCES ability_scores(id) ON DELETE CASCADE,
    description TEXT
);

CREATE TABLE class_skill_choices (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE (class_id, skill_id)
);

CREATE TABLE subclasses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    UNIQUE (class_id, name)
);

CREATE TABLE feats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    prerequisite TEXT,
    benefit TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE feat_ability_bonuses (
    id SERIAL PRIMARY KEY,
    feat_id INTEGER NOT NULL REFERENCES feats(id) ON DELETE CASCADE,
    ability_score_id INTEGER NOT NULL REFERENCES ability_scores(id) ON DELETE CASCADE,
    bonus INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE spells (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    level INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0 AND level <= 9),
    school_id INTEGER NOT NULL REFERENCES magic_schools(id) ON DELETE RESTRICT,
    casting_time VARCHAR(100) NOT NULL,
    range VARCHAR(100) NOT NULL,
    components VARCHAR(20) NOT NULL,
    material_components TEXT,
    duration VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    higher_levels TEXT,
    is_ritual BOOLEAN NOT NULL DEFAULT FALSE,
    is_concentration BOOLEAN NOT NULL DEFAULT FALSE,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE spell_classes (
    spell_id INTEGER NOT NULL REFERENCES spells(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (spell_id, class_id)
);

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
    name VARCHAR(150) NOT NULL UNIQUE,
    type_id INTEGER NOT NULL REFERENCES item_types(id) ON DELETE RESTRICT,
    rarity_id INTEGER NOT NULL REFERENCES item_rarities(id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    attunement_required BOOLEAN NOT NULL DEFAULT FALSE,
    attunement_requirements TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE equipment_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    category_id INTEGER NOT NULL REFERENCES equipment_categories(id) ON DELETE RESTRICT,
    cost_value REAL,
    cost_coin VARCHAR(3) DEFAULT 'gp' CHECK (cost_coin IN ('cp','sp','ep','gp','pp')),
    weight REAL,
    description TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE class_starting_equipment (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    UNIQUE (class_id, equipment_id)
);

CREATE TABLE backgrounds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    feature_name VARCHAR(100),
    feature_description TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
);

CREATE TABLE background_skills (
    background_id INTEGER NOT NULL REFERENCES backgrounds(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (background_id, skill_id)
);

CREATE TABLE tool_proficiencies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE background_tools (
    background_id INTEGER NOT NULL REFERENCES backgrounds(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES tool_proficiencies(id) ON DELETE CASCADE,
    PRIMARY KEY (background_id, tool_id)
);

CREATE INDEX idx_races_source ON races(source_id);
CREATE INDEX idx_subraces_race ON subraces(race_id);
CREATE INDEX idx_classes_source ON classes(source_id);
CREATE INDEX idx_spells_level ON spells(level);
CREATE INDEX idx_spells_school ON spells(school_id);
CREATE INDEX idx_spells_source ON spells(source_id);
CREATE INDEX idx_magic_items_rarity ON magic_items(rarity_id);
CREATE INDEX idx_magic_items_type ON magic_items(type_id);
CREATE INDEX idx_equipment_category ON equipment(category_id);
CREATE INDEX idx_equipment_source ON equipment(source_id);

INSERT INTO sources (name, code, description) VALUES
('Player''s Handbook 2014', 'PH14', 'Книга игрока 2014. Единственный источник, который должен использовать парсер.'),
('Dungeon Master''s Guide', 'DMG', 'Справочный источник, не используется PH14-парсером'),
('Monster Manual', 'MM', 'Справочный источник, не используется PH14-парсером'),
('Xanathar''s Guide to Everything', 'XGE', 'Справочный источник, не используется PH14-парсером'),
('Tasha''s Cauldron of Everything', 'TCE', 'Справочный источник, не используется PH14-парсером')
ON CONFLICT (code) DO NOTHING;

INSERT INTO ability_scores (name, short_name, description) VALUES
('Сила', 'STR', 'Измеряет физическую мощь'),
('Ловкость', 'DEX', 'Измеряет проворство'),
('Телосложение', 'CON', 'Измеряет выносливость'),
('Интеллект', 'INT', 'Измеряет остроту ума'),
('Мудрость', 'WIS', 'Измеряет восприятие и интуицию'),
('Харизма', 'CHA', 'Измеряет силу личности')
ON CONFLICT (name) DO NOTHING;

INSERT INTO magic_schools (name, description) VALUES
('Воплощение', 'Манипуляция энергией'),
('Вызов', 'Призыв существ и предметов'),
('Иллюзия', 'Обман чувств'),
('Некромантия', 'Манипуляция жизнью и смертью'),
('Ограждение', 'Защита и изгнание'),
('Превращение', 'Изменение свойств материи'),
('Прорицание', 'Получение информации'),
('Очарование', 'Влияние на разум')
ON CONFLICT (name) DO NOTHING;

INSERT INTO item_rarities (name) VALUES
('Обычный'), ('Необычный'), ('Редкий'), ('Очень редкий'), ('Легендарный'), ('Артефакт')
ON CONFLICT (name) DO NOTHING;

INSERT INTO item_types (name) VALUES
('Оружие'), ('Доспех'), ('Кольцо'), ('Жезл'), ('Посох'),
('Зелье'), ('Свиток'), ('Чудесный предмет'), ('Щит'), ('Амулет')
ON CONFLICT (name) DO NOTHING;

INSERT INTO equipment_categories (name) VALUES
('Оружие'), ('Доспехи'), ('Инструменты'), ('Вьючные животные'),
('Транспорт'), ('Еда и напитки'), ('Услуги'), ('Амуниция')
ON CONFLICT (name) DO NOTHING;

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
('Сильван', 'Эльфийский', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO tool_proficiencies (name) VALUES
('Инструменты алхимика'), ('Инструменты пивовара'), ('Инструменты каллиграфа'),
('Инструменты плотника'), ('Инструменты картографа'), ('Инструменты сапожника'),
('Инструменты повара'), ('Инструменты стеклодува'), ('Инструменты ювелира'),
('Инструменты кожевника'), ('Инструменты каменщика'), ('Инструменты художника'),
('Инструменты гончара'), ('Инструменты кузнеца'), ('Инструменты ткача'),
('Инструменты резчика по дереву'), ('Воровские инструменты'),
('Инструменты штурмана'), ('Инструменты травника'),
('Набор для грима'), ('Набор для фальсификации'), ('Игровой набор'), ('Музыкальный инструмент')
ON CONFLICT (name) DO NOTHING;

INSERT INTO skills (name, ability_score_id, description) VALUES
('Атлетика', (SELECT id FROM ability_scores WHERE name='Сила'), 'Прыжки, плавание, лазание'),
('Акробатика', (SELECT id FROM ability_scores WHERE name='Ловкость'), 'Равновесие, кувырки'),
('Ловкость рук', (SELECT id FROM ability_scores WHERE name='Ловкость'), 'Карманные кражи, фокусы'),
('Скрытность', (SELECT id FROM ability_scores WHERE name='Ловкость'), 'Прятаться, красться'),
('Анализ', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Поиск улик, дедукция'),
('История', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Исторические события'),
('Магия', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Заклинания, магические традиции'),
('Природа', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Растения, животные, погода'),
('Религия', (SELECT id FROM ability_scores WHERE name='Интеллект'), 'Божества, ритуалы'),
('Восприятие', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Замечать детали'),
('Выживание', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Следопытство, ориентирование'),
('Медицина', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Лечение, диагностика'),
('Проницательность', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Чтение намерений'),
('Уход за животными', (SELECT id FROM ability_scores WHERE name='Мудрость'), 'Дрессировка, успокоение'),
('Выступление', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Развлечение публики'),
('Запугивание', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Угрозы, принуждение'),
('Обман', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Ложь, маскировка'),
('Убеждение', (SELECT id FROM ability_scores WHERE name='Харизма'), 'Дипломатия, переговоры')
ON CONFLICT (name) DO NOTHING;
