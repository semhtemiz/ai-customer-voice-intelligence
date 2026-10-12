SELECT COUNT(*) AS total_reviews,
       COUNT(CASE WHEN rating BETWEEN 1 AND 5 THEN 1 END) AS valid_rating_count,
       COUNT(CASE WHEN recommended_ind IN (0,1) THEN 1 END) AS valid_recommendation_count,
       ROUND(AVG(CASE WHEN rating BETWEEN 1 AND 5 THEN rating END), 2) AS avg_rating,
       ROUND(100.0 * AVG(CASE WHEN recommended_ind IN (0,1) THEN recommended_ind END), 2) AS recommendation_rate_pct,
       ROUND(100.0 * AVG(CASE WHEN rating BETWEEN 1 AND 5
             THEN CASE WHEN rating <= 2 THEN 1.0 ELSE 0.0 END END), 2) AS low_rating_rate_pct
FROM filtered_reviews
