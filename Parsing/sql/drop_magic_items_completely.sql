-- Полное удаление магических предметов из уже созданной БД.
-- Выполни этот файл, если не пересоздаёшь БД через create_database.sql.

DROP TABLE IF EXISTS magic_items CASCADE;
DROP TABLE IF EXISTS item_types CASCADE;
DROP TABLE IF EXISTS item_rarities CASCADE;
