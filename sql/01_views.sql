-- 01_views.sql : dimension tables and analysis views on top of the harmonised tables.
-- Run by src/build_db.py after the parquet files are loaded as tables.

-- ---------- dimensions ----------
CREATE OR REPLACE TABLE dim_experience AS
SELECT * FROM (VALUES
    ('0-4 yrs', 1), ('5-9 yrs', 2), ('10-19 yrs', 3), ('20-29 yrs', 4), ('30+ yrs', 5)
) t(exp_bucket, sort_order);

CREATE OR REPLACE TABLE dim_org_size AS
SELECT DISTINCT org_size, CAST(LEFT(org_size, 1) AS INTEGER) AS sort_order,
       TRIM(SUBSTR(org_size, 3)) AS org_size_label
FROM respondents WHERE org_size IS NOT NULL;

CREATE OR REPLACE TABLE dim_role AS
SELECT role_family, COUNT(*) AS n_total,
       LIST(DISTINCT survey_year ORDER BY survey_year) AS years_present
FROM respondents WHERE role_family IS NOT NULL GROUP BY role_family;

CREATE OR REPLACE TABLE dim_country AS
SELECT country, ANY_VALUE(country_group) AS country_group, COUNT(*) AS n_total
FROM respondents WHERE country IS NOT NULL GROUP BY country;

CREATE OR REPLACE TABLE dim_trust AS
SELECT * FROM (VALUES
    ('1 Highly distrust', 1, 'Distrust'), ('2 Somewhat distrust', 2, 'Distrust'),
    ('3 Neither', 3, 'Neutral'), ('4 Somewhat trust', 4, 'Trust'), ('5 Highly trust', 5, 'Trust')
) t(trust_label, trust_score, trust_group);

-- ---------- analysis views ----------
-- Main scope: professional developers.
CREATE OR REPLACE VIEW v_professionals AS
SELECT * FROM respondents WHERE is_professional = 1;

-- Comparable trust population: current AI users who answered the trust question (same rule every year).
CREATE OR REPLACE VIEW v_trust_users AS
SELECT * FROM respondents WHERE in_trust_base_users = 1;

-- Long format: one row per respondent per segmenting dimension (drives every segment table).
CREATE OR REPLACE VIEW v_resp_dims AS
SELECT resp_id, survey_year, is_professional, uses_ai, ai_use_status, in_trust_base_users,
       trusts_ai, distrusts_ai, highly_distrusts_ai, favorable_ai, dimension, segment
FROM (
    SELECT *, 'All' AS dim_all FROM respondents
) UNPIVOT (segment FOR dimension IN (
    dim_all AS 'Overall',
    exp_bucket AS 'Experience (years coding)',
    role_family AS 'Role',
    org_size AS 'Company size',
    country_group AS 'Country',
    age_group AS 'Age',
    ai_use_frequency AS 'AI use frequency (2025)',
    ai_agents AS 'AI agents (2025)'
));
