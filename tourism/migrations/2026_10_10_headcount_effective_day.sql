-- ========================================
-- Точная дата начала действия лимитов штатного расписания
-- (год + месяц + число)
-- ========================================

-- 1. Добавляем число месяца. Существующие строки получают 1-е число,
--    то есть лимит действует с начала месяца, как и раньше.
ALTER TABLE headcount_limits
    ADD COLUMN effective_day INT NOT NULL DEFAULT 1 AFTER effective_month;

-- 2. Меняем уникальный ключ: теперь лимит уникален в рамках
--    подразделения, должности и полной даты начала действия.
ALTER TABLE headcount_limits DROP INDEX unique_position_period;
ALTER TABLE headcount_limits
    ADD UNIQUE KEY unique_position_period (podrazdelenie, dolzhnost, effective_year, effective_month, effective_day);
