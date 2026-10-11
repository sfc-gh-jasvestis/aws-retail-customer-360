-- Validate the producer contract before building downstream objects.
USE DATABASE IDENTIFIER($DEMO_DB);
USE SCHEMA RAW;
USE WAREHOUSE IDENTIFIER($DEMO_WH);

EXECUTE IMMEDIATE $$
DECLARE
  violations INTEGER;
  invalid_source EXCEPTION (-20001, 'Synthetic source failed grain or measure validation');
BEGIN
  SELECT COUNT(*) INTO :violations FROM (
    SELECT ENTITY_ID, EVENT_DATE
    FROM RAW.COHORT_DAILY
    GROUP BY ENTITY_ID, EVENT_DATE HAVING COUNT(*) <> 1
    UNION ALL
    SELECT observation.ENTITY_ID, observation.EVENT_DATE
    FROM RAW.COHORT_DAILY observation
    LEFT JOIN RAW.COHORTS cohort ON cohort.ID = observation.ENTITY_ID
    WHERE cohort.ID IS NULL OR observation.PURCHASE_COUNT < 0
       OR observation.REVENUE_SGD < 0
       OR observation.CHURNED_COUNT < 0 OR observation.CHURNED_COUNT > observation.ISSUE_COUNT
       OR observation.ISSUE_COUNT > observation.PURCHASE_COUNT
       OR observation.UNSUBSCRIBED > observation.CHURNED_COUNT
       OR observation.TOUCH_DONE > observation.TOUCH_DUE
  );
  IF (violations > 0) THEN
    RAISE invalid_source;
  END IF;
END;
$$;
