-- Synthetic loyalty-cohort-day observations for a fictional Singapore omnichannel retailer (SGD).
-- A cohort is an aggregate group of loyalty members in one Singapore planning area and one
-- shopper segment; no individual customer records exist. Nothing is seeded as a
-- prediction. Randomness is HASH-seeded, so every rebuild is reproducible:
-- per-cohort churn propensity, engagement decay between CRM touches, missed
-- touches, segment-weighted service issue types, issues resolved with the
-- members retained, and two mall-wide checkout outages.
USE DATABASE IDENTIFIER($DEMO_DB);
USE SCHEMA RAW;
USE WAREHOUSE IDENTIFIER($DEMO_WH);

CREATE TABLE RAW.COHORTS AS
WITH cohorts AS (
  SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS COHORT_INDEX
  FROM TABLE(GENERATOR(ROWCOUNT => 48))
), draws AS (
  SELECT COHORT_INDEX,
         MOD(ABS(HASH(COHORT_INDEX, 'sg-c360-tenure')), 1000000) / 1e6 AS U_AGE,
         MOD(ABS(HASH(COHORT_INDEX, 'sg-c360-churnrate')), 1000000) / 1e6 AS U_RATE,
         MOD(ABS(HASH(COHORT_INDEX, 'sg-c360-touch')), 1000000) / 1e6 AS U_TOUCH,
         MOD(ABS(HASH(COHORT_INDEX, 'sg-c360-crm')), 1000000) / 1e6 AS U_DISCIPLINE,
         MOD(ABS(HASH(COHORT_INDEX, 'sg-c360-tier')), 1000000) / 1e6 AS U_TIER
  FROM cohorts
)
SELECT 'COH-' || LPAD(COHORT_INDEX::VARCHAR, 4, '0') AS ID,
       'Synthetic cohort ' || LPAD(COHORT_INDEX::VARCHAR, 4, '0') AS NAME,
       -- Deterministic spread (5 and 8 are coprime): every planning area and segment is present.
       CASE MOD(COHORT_INDEX, 5) WHEN 0 THEN 'Orchard' WHEN 1 THEN 'Tampines'
            WHEN 2 THEN 'Jurong East' WHEN 3 THEN 'Woodlands' ELSE 'Punggol' END AS REGION,
       CASE MOD(COHORT_INDEX, 8) WHEN 0 THEN 'Value shoppers' WHEN 1 THEN 'Value shoppers'
            WHEN 2 THEN 'Value shoppers' WHEN 3 THEN 'Premium loyalists' WHEN 4 THEN 'Premium loyalists'
            WHEN 5 THEN 'Family shoppers' WHEN 6 THEN 'Young professionals' ELSE 'Occasional gifters' END AS SEGMENT,
       COHORT_INDEX,
       1 + FLOOR(U_TIER * 3) AS RISK_TIER,
       ROUND(0.3 + U_AGE * 7.7, 1) AS TENURE_YEARS,
       -- Base daily probability of a churn event 0.5%-2.9%; ~18% of cohorts are
       -- chronically weak (x3).
       (0.005 + U_RATE * 0.024) * IFF(U_RATE > 0.82, 3, 1) AS BASE_CHURN_RATE,
       7 * (1 + FLOOR(U_TOUCH * 3)) AS TOUCH_INTERVAL_DAYS,
       0.5 + U_DISCIPLINE * 0.48 AS TOUCH_COMPLETION_PROB,
       'Active' AS STATUS
FROM draws;

CREATE TABLE RAW.COHORT_DAILY AS
WITH days AS (
  SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS DAY_INDEX
  FROM TABLE(GENERATOR(ROWCOUNT => 90))
), area_events AS (
  -- Two mall-wide checkout outages; every cohort in the planning area raises a
  -- service issue that is resolved once checkout is back.
  SELECT * FROM VALUES (29, 'Jurong East'), (67, 'Woodlands') AS o(DAY_INDEX, REGION)
), base AS (
  SELECT s.ID AS ENTITY_ID, s.COHORT_INDEX, s.SEGMENT, s.REGION, s.TENURE_YEARS,
         s.BASE_CHURN_RATE, s.TOUCH_INTERVAL_DAYS, s.TOUCH_COMPLETION_PROB,
         d.DAY_INDEX,
         DATEADD('day', d.DAY_INDEX - 89, CURRENT_DATE()) AS EVENT_DATE,
         MOD(d.DAY_INDEX + s.COHORT_INDEX * 3, s.TOUCH_INTERVAL_DAYS) AS DAYS_SINCE_TOUCH,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-churn')), 1000000) / 1e6 AS U_CHURN,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-raise')), 1000000) / 1e6 AS U_DETECT,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-retain')), 1000000) / 1e6 AS U_RESOLVE,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-kind')), 1000000) / 1e6 AS U_TYPE,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-touchdone')), 1000000) / 1e6 AS U_DONE,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-baskets')), 1000000) / 1e6 AS U_VOLUME,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-jitter')), 1000000) / 1e6 AS U_NOISE,
         MOD(ABS(HASH(s.ID, d.DAY_INDEX, 'sg-c360-optout')), 1000000) / 1e6 AS U_UNSUB,
         e.REGION IS NOT NULL AS AREA_EVENT
  FROM RAW.COHORTS s CROSS JOIN days d
  LEFT JOIN area_events e ON e.DAY_INDEX = d.DAY_INDEX AND e.REGION = s.REGION
), touches AS (
  SELECT *,
         IFF(DAYS_SINCE_TOUCH = 0, 1, 0) AS TOUCH_DUE,
         IFF(DAYS_SINCE_TOUCH = 0 AND U_DONE < TOUCH_COMPLETION_PROB, 1, 0) AS TOUCH_DONE,
         -- Engagement decay rises between CRM touches; weak touch discipline
         -- carries it over.
         DAYS_SINCE_TOUCH / TOUCH_INTERVAL_DAYS + (1 - TOUCH_COMPLETION_PROB) AS DRIFT
  FROM base
), churns AS (
  SELECT *,
         CASE WHEN U_CHURN < LEAST(0.5, BASE_CHURN_RATE * (0.35 + 1.7 * DRIFT) * (1 + 1.2 / (1 + TENURE_YEARS))) / 4 THEN 2
              WHEN U_CHURN < LEAST(0.5, BASE_CHURN_RATE * (0.35 + 1.7 * DRIFT) * (1 + 1.2 / (1 + TENURE_YEARS))) THEN 1
              ELSE 0 END AS CHURN_RISK_COUNT
  FROM touches
), issues AS (
  SELECT *,
         -- About 82% of at-risk members raise a service issue and then churn;
         -- the rest drift away quietly without raising one.
         IFF(AREA_EVENT, 0, IFF(U_DETECT < 0.82, CHURN_RISK_COUNT, 0)) AS CHURNED_COUNT,
         -- Issues resolved with the members retained: higher for premium segments.
         IFF(AREA_EVENT, 1, IFF(U_RESOLVE < CASE SEGMENT WHEN 'Premium loyalists' THEN 0.22
                                                         WHEN 'Young professionals' THEN 0.15
                                                         WHEN 'Family shoppers' THEN 0.12
                                                         WHEN 'Value shoppers' THEN 0.10 ELSE 0.07 END, 1, 0)) AS RESOLVED_COUNT
  FROM churns
), measured AS (
  SELECT *,
         CHURNED_COUNT + RESOLVED_COUNT AS ISSUE_COUNT,
         ROUND(CASE SEGMENT WHEN 'Value shoppers' THEN 520 WHEN 'Premium loyalists' THEN 140
                            WHEN 'Family shoppers' THEN 260 WHEN 'Young professionals' THEN 300 ELSE 90 END
               * (0.7 + 0.6 * U_VOLUME) * (1 + 0.6 * CHURN_RISK_COUNT)) AS PURCHASE_COUNT,
         CASE SEGMENT WHEN 'Value shoppers' THEN 51 WHEN 'Premium loyalists' THEN 196
                      WHEN 'Family shoppers' THEN 97 WHEN 'Young professionals' THEN 73 ELSE 119 END
           * (0.8 + 0.4 * U_NOISE) AS AVG_BASKET_SGD
  FROM issues
)
SELECT ENTITY_ID || '-' || TO_CHAR(EVENT_DATE, 'YYYYMMDD') AS EVENT_ID,
       ENTITY_ID, EVENT_DATE,
       PURCHASE_COUNT,
       ROUND(PURCHASE_COUNT * AVG_BASKET_SGD, 0) AS REVENUE_SGD,
       ISSUE_COUNT, CHURNED_COUNT,
       IFF(CHURNED_COUNT > 0 AND U_UNSUB < 0.55, 1, 0) AS UNSUBSCRIBED,
       CASE WHEN ISSUE_COUNT = 0 THEN 'None'
            WHEN AREA_EVENT THEN 'Mall checkout outage'
            WHEN SEGMENT = 'Value shoppers' THEN IFF(U_TYPE < 0.45, 'Promotion not applied', IFF(U_TYPE < 0.8, 'Points not credited', 'Price match dispute'))
            WHEN SEGMENT = 'Premium loyalists' THEN IFF(U_TYPE < 0.4, 'Points not credited', IFF(U_TYPE < 0.75, 'Tier benefit not honoured', 'Delivery delay'))
            WHEN SEGMENT = 'Family shoppers' THEN IFF(U_TYPE < 0.55, 'Delivery delay', 'Out of stock after order')
            WHEN SEGMENT = 'Young professionals' THEN IFF(U_TYPE < 0.45, 'App checkout failure', IFF(U_TYPE < 0.8, 'Delivery delay', 'Out of stock after order'))
            ELSE IFF(U_TYPE < 0.5, 'Gift card problem', IFF(U_TYPE < 0.75, 'Delivery delay', 'Promotion not applied')) END AS ISSUE_TYPE,
       TOUCH_DUE, TOUCH_DONE,
       ROUND(0.8 + 2.2 * DRIFT + 2.6 * CHURN_RISK_COUNT + U_NOISE * 0.9, 2) AS RETURN_RATE_PCT,
       ROUND(6 + 9 * DRIFT + 11 * CHURN_RISK_COUNT + U_NOISE * 4, 1) AS AVG_RESPONSE_HRS,
       CURRENT_TIMESTAMP() AS LOADED_AT
FROM measured;

-- Loyalty profile field completeness per cohort (aggregate snapshot).
CREATE TABLE RAW.PROFILE_FIELDS AS
SELECT ID AS ENTITY_ID,
       CASE SEGMENT WHEN 'Value shoppers' THEN 'Channel preference'
                    WHEN 'Premium loyalists' THEN 'Size and fit profile'
                    WHEN 'Family shoppers' THEN 'Household profile'
                    WHEN 'Young professionals' THEN 'Notification preference'
                    ELSE 'Gift occasion profile' END AS DOC_TYPE,
       1 + MOD(ABS(HASH(ID, 'sg-c360-fields')), 4) AS REQUIRED_QTY,
       MOD(ABS(HASH(ID, 'sg-c360-filled')), 5) AS ON_FILE_QTY,
       IFF(MOD(ABS(HASH(ID, 'sg-c360-filled')), 5) < 1 + MOD(ABS(HASH(ID, 'sg-c360-fields')), 4),
           MOD(ABS(HASH(ID, 'sg-c360-awaiting')), 3), 0) AS PENDING_QTY,
       CURRENT_DATE() AS SNAPSHOT_DATE
FROM RAW.COHORTS;
