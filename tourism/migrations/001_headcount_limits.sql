-- ========================================
-- Таблица штатного расписания (лимиты по должности)
-- ========================================
CREATE TABLE IF NOT EXISTS headcount_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    podrazdelenie VARCHAR(100) NOT NULL,
    dolzhnost VARCHAR(200) NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    max_count INT NOT NULL COMMENT 'Максимальное кол-во сотрудников',
    occupancy_hint VARCHAR(50) DEFAULT NULL COMMENT 'Загрузка отеля (для будущего)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_limit (podrazdelenie, dolzhnost, year, month)
);

-- ========================================
-- История нарушений штатного расписания
-- ========================================
CREATE TABLE IF NOT EXISTS violation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    podrazdelenie VARCHAR(100) NOT NULL,
    dolzhnost VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    limit_count INT NOT NULL,
    fact_count INT NOT NULL,
    excess INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (date),
    INDEX idx_month (year, month)
);
