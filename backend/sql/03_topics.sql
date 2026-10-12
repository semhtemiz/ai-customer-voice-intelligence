SELECT rt.topic, COUNT(DISTINCT rt.review_id) AS mentions
FROM review_topics rt
JOIN filtered_candidates fc ON fc.review_id=rt.review_id
JOIN review_topic_results tr ON tr.review_id=rt.review_id AND tr.run_id=rt.run_id
WHERE rt.run_id=:topic_run_id AND tr.status='completed'
GROUP BY rt.topic ORDER BY mentions DESC, rt.topic ASC
