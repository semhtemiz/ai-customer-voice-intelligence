SELECT COALESCE(department_name, 'Unknown') AS department,
       COUNT(*) AS reviews,
       COUNT(rating) AS valid_rating_count,
       ROUND(AVG(rating), 2) AS avg_rating,
       ROUND(100.0 * AVG(CASE WHEN rating IS NOT NULL
             THEN CASE WHEN rating <= 2 THEN 1.0 ELSE 0.0 END END), 2) AS low_rating_rate_pct
FROM filtered_reviews
GROUP BY COALESCE(department_name, 'Unknown')
ORDER BY reviews DESC, department ASC
