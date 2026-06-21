-- Очистка старых заклинаний перед повторным парсингом.
DELETE FROM spell_classes;
DELETE FROM spells;

-- Также удали файл кэша, если он есть:
-- Parsing/cache/spell_links_PH14.json
-- Parsing/cache/spell_links_PH14_full_scan.json
