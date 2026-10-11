-- ============================================================================
-- 06_INTELLIGENCE.SQL - search, anomaly detection, semantic view, agent,
-- live-engagement alert and on-demand refresh DAG.
-- Run with snowflake/run_intelligence.py (substitutes checked __DEMO_DB__ /
-- __DEMO_WH__ / __ALERT_EMAIL__). Requires 00-05, plus 08 (Snowflake only) or
-- aws/setup_aws.py (AWS build) for RAW.LIVE_ENGAGEMENT.
-- Alerts and tasks are created SUSPENDED; run them with EXECUTE ALERT / EXECUTE TASK.
-- ============================================================================
USE DATABASE __DEMO_DB__;
CREATE SCHEMA IF NOT EXISTS SEARCH;
CREATE SCHEMA IF NOT EXISTS APP;

-- ---------- Synthetic service-issue knowledge base (clearly synthetic SOPs) ----------
CREATE OR REPLACE TABLE SEARCH.ISSUE_DOCS AS
WITH types AS (
  SELECT DISTINCT r.ISSUE_TYPE, a.SEGMENT
  FROM RAW.COHORT_DAILY r JOIN RAW.COHORTS a ON a.ID = r.ENTITY_ID
  WHERE r.CHURNED_COUNT > 0
)
SELECT
  'SOP-' || LPAD(ROW_NUMBER() OVER (ORDER BY SEGMENT, ISSUE_TYPE)::VARCHAR, 3, '0') AS DOC_ID,
  'SOP' AS DOC_TYPE,
  SEGMENT,
  ISSUE_TYPE,
  SEGMENT || ' - ' || ISSUE_TYPE || ' service issue handling' AS TITLE,
  'Synthetic demo SOP. Shopper segment: ' || SEGMENT || '. Service issue type: ' || ISSUE_TYPE || '. '
  || 'Step 1: open a retention case against the cohort, acknowledge the affected members through their preferred channel within 4 hours, and pause promotional sends to that cohort until an agent triages the case. '
  || 'Step 2: ' || CASE
       WHEN ISSUE_TYPE = 'Points not credited' THEN 'reconcile the loyalty ledger against the purchase records, post the missing points in one batch, and add a goodwill points top-up for members who raised the issue twice.'
       WHEN ISSUE_TYPE = 'Promotion not applied' THEN 'check the promotion rules against the basket, refund the difference to the original payment method, and correct the promotion configuration before the next send.'
       WHEN ISSUE_TYPE = 'Price match dispute' THEN 'compare the claimed price with the published price list, honour the match when the policy allows it, and log the outcome for the pricing team.'
       WHEN ISSUE_TYPE = 'Tier benefit not honoured' THEN 'confirm the tier status on the member profile, apply the missed benefit, and brief the store or service team that declined it.'
       WHEN ISSUE_TYPE = 'Delivery delay' THEN 'share a revised delivery window, waive the delivery fee for the order, and flag the fulfilment partner when the delay exceeds 48 hours.'
       WHEN ISSUE_TYPE = 'Out of stock after order' THEN 'offer the closest substitute or a full refund, and send a back-in-stock notice when the item returns.'
       WHEN ISSUE_TYPE = 'App checkout failure' THEN 'capture the app version and payment method, retry the order on behalf of the member, and raise a ticket with the digital team.'
       WHEN ISSUE_TYPE = 'Gift card problem' THEN 'verify the gift card balance and activation, reissue a replacement card, and confirm the new balance to the member.'
       ELSE 'review the issue against the cohort history and escalate to a team lead if the cause is unclear.'
     END
  || ' Step 3: keep the case open and schedule a cohort retention review when, after triage, the cohort return rate is above 5% or the average service response time is above 24 hours. '
  || 'Step 4: close the case with the outcome; for members who churned or unsubscribed, add the cohort to the next win-back campaign and to the weekly customer health report.' AS CONTENT
FROM types;

CREATE OR REPLACE CORTEX SEARCH SERVICE SEARCH.ISSUE_SOP_SEARCH
  ON CONTENT
  ATTRIBUTES SEGMENT, ISSUE_TYPE
  WAREHOUSE = __DEMO_WH__
  TARGET_LAG = '7 days'
AS (SELECT DOC_ID, TITLE, SEGMENT, ISSUE_TYPE, CONTENT FROM SEARCH.ISSUE_DOCS);

-- ---------- Return rate anomaly detection (train first 75 days, detect last 15) ----------
CREATE OR REPLACE VIEW ML.RETURN_RATE_SERIES AS
SELECT ENTITY_ID, EVENT_DATE::TIMESTAMP_NTZ AS TS, RETURN_RATE_PCT::FLOAT AS RETURN_RATE
FROM RAW.COHORT_DAILY;
CREATE OR REPLACE VIEW ML.RETURN_RATE_TRAIN AS
SELECT * FROM ML.RETURN_RATE_SERIES WHERE TS < (SELECT DATEADD(day, -15, MAX(TS)) FROM ML.RETURN_RATE_SERIES);
CREATE OR REPLACE VIEW ML.RETURN_RATE_DETECT AS
SELECT * FROM ML.RETURN_RATE_SERIES WHERE TS >= (SELECT DATEADD(day, -15, MAX(TS)) FROM ML.RETURN_RATE_SERIES);

CREATE OR REPLACE SNOWFLAKE.ML.ANOMALY_DETECTION ML.RETURN_RATE_ANOMALY_MODEL(
  INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'ML.RETURN_RATE_TRAIN'),
  SERIES_COLNAME => 'ENTITY_ID', TIMESTAMP_COLNAME => 'TS', TARGET_COLNAME => 'RETURN_RATE',
  LABEL_COLNAME => '');

CREATE OR REPLACE TABLE ML.RETURN_RATE_ANOMALIES AS
SELECT SERIES::VARCHAR AS ENTITY_ID, TS::DATE AS EVENT_DATE, Y AS RETURN_RATE, FORECAST AS EXPECTED,
       LOWER_BOUND, UPPER_BOUND, IS_ANOMALY, PERCENTILE
FROM TABLE(ML.RETURN_RATE_ANOMALY_MODEL!DETECT_ANOMALIES(
  INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'ML.RETURN_RATE_DETECT'),
  SERIES_COLNAME => 'ENTITY_ID', TIMESTAMP_COLNAME => 'TS', TARGET_COLNAME => 'RETURN_RATE'));

-- ---------- Semantic view ----------
CREATE OR REPLACE SEMANTIC VIEW APP.CUSTOMER360_ANALYTICS
  TABLES (
    cohorts AS CURATED.PERFORMANCE_SUMMARY PRIMARY KEY (ENTITY_ID)
      WITH SYNONYMS = ('entities', 'customer cohorts', 'segments of members')
      COMMENT = 'One row per loyalty cohort (Singapore planning area and shopper segment), 90-day aggregate totals',
    risk AS ML.CHURN_RISK_SCORES PRIMARY KEY (ENTITY_ID)
      COMMENT = 'Latest next-7-day churn probability per cohort',
    issues AS CURATED.ISSUE_SUMMARY PRIMARY KEY (ISSUE_TYPE)
      COMMENT = 'Service issues, churned members and unsubscribes by issue type, 90 days',
    daily AS CURATED.TREND_ANALYSIS PRIMARY KEY (METRIC_DATE)
      COMMENT = 'Retailer-wide totals per day'
  )
  RELATIONSHIPS (risk_cohort AS risk (ENTITY_ID) REFERENCES cohorts)
  FACTS (
    cohorts.issues_f AS ISSUE_COUNT,
    cohorts.churned_f AS CHURNED_COUNT,
    cohorts.unsub_f AS UNSUBSCRIBE_COUNT,
    cohorts.purchases_f AS PURCHASE_COUNT,
    cohorts.revenue_f AS REVENUE_SGD,
    cohorts.touch_due_f AS TOUCH_DUE,
    cohorts.touch_done_f AS TOUCH_DONE,
    risk.churn_prob_f AS CHURN_PROB_7D,
    issues.type_issues_f AS ISSUE_COUNT,
    issues.type_churned_f AS CHURNED_COUNT,
    issues.type_unsub_f AS UNSUBSCRIBE_COUNT,
    issues.type_revenue_f AS EXPOSED_REVENUE_SGD,
    daily.day_issues_f AS ISSUE_COUNT,
    daily.day_churned_f AS CHURNED_COUNT,
    daily.day_revenue_f AS REVENUE_SGD
  )
  DIMENSIONS (
    cohorts.cohort_id AS ENTITY_ID WITH SYNONYMS = ('cohort', 'customer cohort', 'entity', 'member group'),
    cohorts.cohort_name AS ENTITY_NAME,
    cohorts.planning_area AS REGION WITH SYNONYMS = ('planning area', 'region', 'town', 'location')
      COMMENT = 'Singapore planning area where the cohort shops',
    cohorts.segment AS SEGMENT WITH SYNONYMS = ('shopper segment', 'customer segment'),
    cohorts.risk_tier AS RISK_TIER COMMENT = 'Cohort retention risk tier 1 (low) to 3 (high)',
    risk.risk_band AS RISK_BAND COMMENT = 'High >= 0.5, Medium >= 0.25, else Low',
    risk.scored_as_of AS SCORED_AS_OF,
    issues.issue_type AS ISSUE_TYPE WITH SYNONYMS = ('issue', 'complaint type', 'issue reason'),
    daily.metric_date AS METRIC_DATE
  )
  METRICS (
    cohorts.cohort_count AS COUNT(cohorts.cohort_id) WITH SYNONYMS = ('number of cohorts', 'number of entities', 'how many cohorts'),
    cohorts.clean_purchase_rate_pct AS 100 * (SUM(cohorts.purchases_f) - SUM(cohorts.issues_f)) / NULLIF(SUM(cohorts.purchases_f), 0)
      WITH SYNONYMS = ('issue-free purchase rate', 'clean purchase rate')
      COMMENT = 'Purchases without a service issue / purchases made',
    cohorts.issue_churn_pct AS 100 * SUM(cohorts.churned_f) / NULLIF(SUM(cohorts.issues_f), 0)
      COMMENT = 'Churned members / service issues raised',
    cohorts.issues_raised AS SUM(cohorts.issues_f) WITH SYNONYMS = ('service issues', 'complaints'),
    cohorts.churned_members AS SUM(cohorts.churned_f) WITH SYNONYMS = ('churn', 'lapsed members', 'churned'),
    cohorts.unsubscribes AS SUM(cohorts.unsub_f) WITH SYNONYMS = ('unsubscribed', 'opt-outs'),
    cohorts.purchases_made AS SUM(cohorts.purchases_f) WITH SYNONYMS = ('purchases', 'transactions'),
    cohorts.total_revenue_sgd AS SUM(cohorts.revenue_f) WITH SYNONYMS = ('revenue', 'sales', 'sales in SGD'),
    cohorts.touch_compliance_pct AS 100 * SUM(cohorts.touch_done_f) / NULLIF(SUM(cohorts.touch_due_f), 0)
      COMMENT = 'CRM touches completed / CRM touches due',
    risk.avg_churn_prob AS AVG(risk.churn_prob_f),
    issues.type_issues AS SUM(issues.type_issues_f),
    issues.type_churned AS SUM(issues.type_churned_f),
    issues.type_unsub AS SUM(issues.type_unsub_f),
    issues.type_churn_share_pct AS 100 * SUM(issues.type_churned_f) / NULLIF(SUM(issues.type_issues_f), 0),
    daily.daily_issues AS SUM(daily.day_issues_f),
    daily.daily_churned AS SUM(daily.day_churned_f),
    daily.daily_revenue_sgd AS SUM(daily.day_revenue_f)
  )
  COMMENT = 'Synthetic Singapore retail customer 360 analytics (demo)';

-- ---------- Cortex Agent ----------
CREATE OR REPLACE AGENT APP.CUSTOMER360_AGENT
  COMMENT = 'Customer 360 assistant over synthetic loyalty cohorts of a fictional Singapore retailer'
  FROM SPECIFICATION
$$
models:
  orchestration: claude-sonnet-4-5
instructions:
  response: "Answer only from tool results. State that data is synthetic. Give cohort IDs and numbers with units (SGD, %)."
  orchestration: "Use customer360_analyst for purchases, revenue, service issues, churned members, unsubscribes, issue-free purchase rate, CRM touch compliance, cohorts, planning areas, segments, issue types and churn risk. Use sop_search for service-issue handling procedures."
tools:
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: customer360_analyst
      description: "Purchases, revenue in SGD, service issues, churned members, unsubscribes, issue-free purchase rate, CRM touch compliance, issue types and churn risk scores by cohort, planning area and segment"
  - tool_spec:
      type: cortex_search
      name: sop_search
      description: "Synthetic service-issue handling SOPs by shopper segment and issue type"
tool_resources:
  customer360_analyst:
    semantic_view: __DEMO_DB__.APP.CUSTOMER360_ANALYTICS
    execution_environment:
      type: warehouse
      warehouse: __DEMO_WH__
  sop_search:
    name: __DEMO_DB__.SEARCH.ISSUE_SOP_SEARCH
    max_results: 3
    id_column: DOC_ID
    title_column: TITLE
$$;

-- ---------- Live-engagement alert ----------
CREATE TABLE IF NOT EXISTS APP.ALERT_LOG (
  ALERTED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(), COHORT_ID VARCHAR,
  EVENT_TS TIMESTAMP_NTZ, AMOUNT_SGD FLOAT, RESPONSE_MINUTES FLOAT, SOP_HINT VARCHAR);

CREATE OR REPLACE NOTIFICATION INTEGRATION SG_RETAIL_CUSTOMER_360_EMAIL_INT
  TYPE = EMAIL ENABLED = TRUE ALLOWED_RECIPIENTS = ('__ALERT_EMAIL__');

CREATE OR REPLACE PROCEDURE APP.LOG_LIVE_ALERTS()
RETURNS NUMBER
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  n NUMBER;
BEGIN
  INSERT INTO APP.ALERT_LOG (COHORT_ID, EVENT_TS, AMOUNT_SGD, RESPONSE_MINUTES, SOP_HINT)
    SELECT p.COHORT_ID, p.EVENT_TS, p.AMOUNT_SGD, p.RESPONSE_MINUTES,
           'Check ' || r.SEGMENT || ' service-issue SOPs; current risk band ' || COALESCE(s.RISK_BAND, 'n/a')
    FROM RAW.LIVE_ENGAGEMENT p
    JOIN RAW.COHORTS r ON r.ID = p.COHORT_ID
    LEFT JOIN ML.CHURN_RISK_SCORES s ON s.ENTITY_ID = p.COHORT_ID
    WHERE p.STATUS = 'ISSUE'
      AND NOT EXISTS (SELECT 1 FROM APP.ALERT_LOG l WHERE l.COHORT_ID = p.COHORT_ID AND l.EVENT_TS = p.EVENT_TS);
  n := SQLROWCOUNT;
  IF (n > 0) THEN
    CALL SYSTEM$SEND_EMAIL('SG_RETAIL_CUSTOMER_360_EMAIL_INT', '__ALERT_EMAIL__',
      '[Demo] Service issue alert',
      'New live service issues logged in APP.ALERT_LOG: ' || :n || '. Data is synthetic.');
  END IF;
  RETURN n;
END;
$$;

CREATE OR REPLACE ALERT APP.LIVE_ENGAGEMENT_ALERT
  WAREHOUSE = __DEMO_WH__
  SCHEDULE = '5 MINUTE'
  IF (EXISTS (
    SELECT 1 FROM RAW.LIVE_ENGAGEMENT p
    WHERE p.STATUS = 'ISSUE'
      AND NOT EXISTS (SELECT 1 FROM APP.ALERT_LOG l WHERE l.COHORT_ID = p.COHORT_ID AND l.EVENT_TS = p.EVENT_TS)))
  THEN CALL APP.LOG_LIVE_ALERTS();

-- ---------- On-demand refresh DAG (suspended; run with EXECUTE TASK APP.TASK_REFRESH_CURATED) ----------
CREATE OR REPLACE PROCEDURE APP.REFRESH_CURATED()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
  ALTER DYNAMIC TABLE CURATED.PERFORMANCE_SUMMARY REFRESH;
  ALTER DYNAMIC TABLE CURATED.TREND_ANALYSIS REFRESH;
  ALTER DYNAMIC TABLE CURATED.ISSUE_SUMMARY REFRESH;
  ALTER DYNAMIC TABLE CURATED.KPI_SUMMARY REFRESH;
  RETURN 'refreshed';
END;
$$;

CREATE OR REPLACE TASK APP.TASK_REFRESH_CURATED
  WAREHOUSE = __DEMO_WH__
AS
  CALL APP.REFRESH_CURATED();

CREATE OR REPLACE TASK APP.TASK_RESCORE_RISK
  WAREHOUSE = __DEMO_WH__
  AFTER APP.TASK_REFRESH_CURATED
AS
  CREATE OR REPLACE TABLE ML.CHURN_RISK_SCORES COPY GRANTS AS
  WITH latest AS (
    SELECT * FROM ML.CHURN_FEATURES QUALIFY ROW_NUMBER() OVER (PARTITION BY ENTITY_ID ORDER BY EVENT_DATE DESC) = 1
  ), p AS (
    SELECT ENTITY_ID, EVENT_DATE,
           ML.CHURN_RISK_MODEL!PREDICT(INPUT_DATA => OBJECT_CONSTRUCT(
             'SEGMENT', SEGMENT, 'RISK_TIER', RISK_TIER, 'TENURE_YEARS', TENURE_YEARS,
             'RETURN_RATE_PCT', RETURN_RATE_PCT, 'AVG_RESPONSE_HRS', AVG_RESPONSE_HRS,
             'RETURN_RATE_7D', RETURN_RATE_7D, 'CHURNED_30D', CHURNED_30D)) AS PRED
    FROM latest
  )
  SELECT ENTITY_ID, EVENT_DATE AS SCORED_AS_OF, ROUND(PRED:probability:CHURN::FLOAT, 4) AS CHURN_PROB_7D,
         CASE WHEN PRED:probability:CHURN::FLOAT >= 0.5 THEN 'High'
              WHEN PRED:probability:CHURN::FLOAT >= 0.25 THEN 'Medium' ELSE 'Low' END AS RISK_BAND,
         CURRENT_TIMESTAMP() AS SCORED_AT
  FROM p;
