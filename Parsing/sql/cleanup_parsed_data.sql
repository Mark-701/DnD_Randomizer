-- Очистка только таблиц, которые заполняет парсер.
-- Справочники ability_scores, skills, magic_schools и т.п. не удаляются. Магические предметы исключены из проекта.
DELETE FROM background_tools;
DELETE FROM background_skills;
DELETE FROM backgrounds;
DELETE FROM class_starting_equipment;
DELETE FROM class_skill_choices;
DELETE FROM subclasses;
DELETE FROM spell_classes;
DELETE FROM spells;
DELETE FROM feat_ability_bonuses;
DELETE FROM feats;
DELETE FROM race_ability_bonuses;
DELETE FROM race_languages;
DELETE FROM subraces;
DELETE FROM races;
DELETE FROM equipment;
DELETE FROM classes;
