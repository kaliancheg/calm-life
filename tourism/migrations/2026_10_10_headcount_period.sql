-- ========================================
-- Привязка лимитов штатного расписания к периоду (месяц/год)
-- и защита violation_history от дублей
-- ========================================

-- 1. Добавляем период действия лимита в headcount_limits.
--    Существующие строки получают период по умолчанию (2000-01), чтобы
--    они действовали как «базовые» до первой загрузки с явным периодом.
ALTER TABLE headcount_limits
    ADD COLUMN effective_year INT NOT NULL DEFAULT 2000 AFTER dolzhnost,
    ADD COLUMN effective_month INT NOT NULL DEFAULT 1 AFTER effective_year;

-- 2. Меняем уникальный ключ: лимит уникален в рамках подразделения,
--    должности и периода (месяц/год).
ALTER TABLE headcount_limits DROP INDEX unique_position;
ALTER TABLE headcount_limits
    ADD UNIQUE KEY unique_position_period (podrazdelenie, dolzhnost, effective_year, effective_month);

-- 3. Чистим уже накопившиеся дубли в violation_history:
--    оставляем по одной (последней) записи на ключ podrazdelenie+dolzhnost+date.
--    Используем временную таблицу с max(id) — это O(n log n) вместо O(n^2)
--    self-join, поэтому на большой истории выполняется быстро и не «вешает» БД.
CREATE TEMPORARY TABLE vh_keep AS
SELECT MAX(id) AS keep_id
FROM violation_history
GROUP BY podrazdelenie, dolzhnost, date;

DELETE vh FROM violation_history vh
LEFT JOIN vh_keep k ON vh.id = k.keep_id
WHERE k.keep_id IS NULL;

DROP TEMPORARY TABLE vh_keep;

-- 4. Уникальный ключ, чтобы история нарушений больше не раздувалась.
ALTER TABLE violation_history
    ADD UNIQUE KEY unique_violation (podrazdelenie, dolzhnost, date);
