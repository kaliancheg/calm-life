-- ========================================
-- v2.5.20 — Динамические лимиты по загрузке отеля
-- ========================================

-- 1. Переделываем headcount_limits: убираем year/month, 3 лимита
DROP TABLE IF EXISTS headcount_limits;

CREATE TABLE headcount_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    podrazdelenie VARCHAR(100) NOT NULL COMMENT 'Подразделение: Волна / Арт_Лайф',
    dolzhnost VARCHAR(200) NOT NULL COMMENT 'Должность',
    limit_1 INT NOT NULL DEFAULT 0 COMMENT 'Лимит при загрузке ≥70%',
    limit_2 INT NOT NULL DEFAULT 0 COMMENT 'Лимит при загрузке 50–69%',
    limit_3 INT NOT NULL DEFAULT 0 COMMENT 'Лимит при загрузке <50%',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_position (podrazdelenie, dolzhnost)
);

-- 2. Таблица загрузки отеля по дням
CREATE TABLE IF NOT EXISTS hotel_occupancy (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    podrazdelenie VARCHAR(100) NOT NULL COMMENT 'Подразделение: Волна / Арт_Лайф',
    occupancy_percent DECIMAL(5,2) NOT NULL COMMENT 'Процент загрузки (например 75.48)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_occupancy (date, podrazdelenie),
    INDEX idx_date (date)
);

-- 3. Переделываем violation_history под новый формат
DROP TABLE IF EXISTS violation_history;

CREATE TABLE violation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    podrazdelenie VARCHAR(100) NOT NULL,
    dolzhnost VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    limit_level VARCHAR(15) NOT NULL COMMENT 'Уровень загрузки: >=70, 50-69, <50',
    limit_count INT NOT NULL COMMENT 'Применённый лимит',
    fact_count INT NOT NULL,
    excess INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (date),
    INDEX idx_month (date)
);
