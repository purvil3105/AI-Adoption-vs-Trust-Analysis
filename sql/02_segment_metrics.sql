-- 02_segment_metrics.sql : adoption vs trust by year and segment (professional developers).
-- adoption base = answered "Do you currently use AI tools?"; trust base = current AI users (comparable).
-- Segments with fewer than 100 respondents in the trust base are suppressed.

CREATE OR REPLACE TABLE segment_metrics AS
WITH agg AS (
    SELECT survey_year, dimension, segment,
           COUNT(*) FILTER (WHERE ai_use_status IS NOT NULL)        AS n_adoption,
           AVG(uses_ai)                                              AS adoption_rate,
           COUNT(*) FILTER (WHERE in_trust_base_users = 1)          AS n_trust,
           AVG(trusts_ai)    FILTER (WHERE in_trust_base_users = 1) AS trust_rate,
           AVG(distrusts_ai) FILTER (WHERE in_trust_base_users = 1) AS distrust_rate,
           AVG(highly_distrusts_ai) FILTER (WHERE in_trust_base_users = 1) AS highly_distrust_rate,
           AVG(favorable_ai) FILTER (WHERE uses_ai = 1)             AS favorable_rate
    FROM v_resp_dims
    WHERE is_professional = 1
    GROUP BY ALL
)
SELECT *,
       adoption_rate - trust_rate                                    AS trust_gap,
       1.96 * SQRT(trust_rate * (1 - trust_rate) / n_trust)          AS trust_moe,
       1.96 * SQRT(distrust_rate * (1 - distrust_rate) / n_trust)    AS distrust_moe
FROM agg
WHERE n_trust >= 100
ORDER BY dimension, segment, survey_year;

-- Trust by type of AI use (task), current AI users, professional developers.
CREATE OR REPLACE TABLE task_trust AS
SELECT t.survey_year, t.task,
       COUNT(DISTINCT r.resp_id)  AS n_users,
       AVG(r.trusts_ai)           AS trust_rate,
       AVG(r.distrusts_ai)        AS distrust_rate
FROM respondent_ai_tasks t
JOIN respondents r USING (resp_id)
WHERE r.is_professional = 1 AND r.in_trust_base_users = 1 AND t.task <> 'other'
GROUP BY ALL
HAVING COUNT(DISTINCT r.resp_id) >= 100
ORDER BY t.survey_year, distrust_rate DESC;

-- Trust by AI tool / model actually used (descriptive only; 2025 asks about models, not products).
CREATE OR REPLACE TABLE tool_trust AS
SELECT t.survey_year, t.tool, t.vendor, t.tool_kind,
       COUNT(DISTINCT r.resp_id)  AS n_users,
       AVG(r.trusts_ai)           AS trust_rate,
       AVG(r.distrusts_ai)        AS distrust_rate
FROM respondent_ai_tools t
JOIN respondents r USING (resp_id)
WHERE r.is_professional = 1 AND r.in_trust_base_users = 1
GROUP BY ALL
HAVING COUNT(DISTINCT r.resp_id) >= 100
ORDER BY t.survey_year, n_users DESC;

-- Year-level headline (comparable definitions).
CREATE OR REPLACE TABLE headline AS
SELECT survey_year,
       COUNT(*)                                                     AS n_respondents,
       AVG(uses_ai)                                                 AS adoption_all,
       AVG(uses_ai) FILTER (WHERE is_professional = 1)              AS adoption_prof,
       AVG(uses_or_plans_ai)                                        AS use_or_plan_all,
       AVG(trusts_ai)    FILTER (WHERE in_trust_base_users = 1 AND is_professional = 1) AS trust_users_prof,
       AVG(distrusts_ai) FILTER (WHERE in_trust_base_users = 1 AND is_professional = 1) AS distrust_users_prof,
       AVG(trusts_ai)    FILTER (WHERE in_trust_base_official = 1)  AS trust_official,
       AVG(distrusts_ai) FILTER (WHERE in_trust_base_official = 1)  AS distrust_official
FROM respondents
GROUP BY survey_year
ORDER BY survey_year;
