-- ============================================================
--  Archives Library — MySQL Database Setup Script
--  Run this in phpMyAdmin → SQL tab, or via MySQL CLI
-- ============================================================

-- 1. Create the database
CREATE DATABASE IF NOT EXISTS archives_library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE archives_library;

-- 2. (Optional) Create a dedicated MySQL user
--    Uncomment the lines below if you want a dedicated DB user
--    instead of using root.
--
-- CREATE USER IF NOT EXISTS 'archives_user'@'localhost' IDENTIFIED BY 'archives_pass_2025';
-- GRANT ALL PRIVILEGES ON archives_library.* TO 'archives_user'@'localhost';
-- FLUSH PRIVILEGES;
--
-- Then update settings.py:
--   'USER': 'archives_user',
--   'PASSWORD': 'archives_pass_2025',

-- ============================================================
-- NOTE: Do NOT run CREATE TABLE statements here.
-- Django's migration system will create all tables automatically
-- when you run:  python manage.py migrate
-- ============================================================

SELECT 'Database archives_library is ready.' AS status;
