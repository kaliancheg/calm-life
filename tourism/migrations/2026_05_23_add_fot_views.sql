-- Миграция: создание представлений/витрин для ускорения агрегаций ФОТ
-- Эта миграция создаёт простое представление daily_records_agg

CREATE OR REPLACE VIEW daily_records_agg AS
SELECT
  DATE(data) AS day,
  podrazdelenie,
  otdel,
  dolzhnost,
  SUM(itogo) AS total_money,
  SUM(chasy) AS total_hours,
  SUM(nachisleno) AS total_nachisleno,
  COUNT(DISTINCT fio) AS employees,
  COUNT(*) AS records
FROM records
GROUP BY DATE(data), podrazdelenie, otdel, dolzhnost;

-- Для больших объёмов данных рекомендуется заменить VIEW на материализованную таблицу
-- и запускать nightly ETL для наполнения/обновления.
