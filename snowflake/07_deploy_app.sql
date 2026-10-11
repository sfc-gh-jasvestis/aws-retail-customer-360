-- ============================================================================
-- 07_deploy_app.sql - deploy the Next.js app to SPCS.
-- Replace placeholders through snowflake/run_intelligence.py --files 07_deploy_app.sql
-- (checked __DEMO_DB__ / __DEMO_WH__). Build and push the image first:
--   snow spcs image-registry login -c <connection>
--   docker build --platform linux/amd64 -t <repository_url>/sg-retail-customer-360-app:v1 app
--   docker push <repository_url>/sg-retail-customer-360-app:v1
-- Existing service: rerun the spec below as ALTER SERVICE APP.SG_RETAIL_CUSTOMER_360_APP FROM SPECIFICATION $$...$$.
-- Runs on an existing compute pool passed as --compute-pool.
-- ============================================================================
CREATE IMAGE REPOSITORY IF NOT EXISTS APP.IMAGES;

CREATE SERVICE IF NOT EXISTS APP.SG_RETAIL_CUSTOMER_360_APP
  -- DEMO_PLATFORM (from --platform): snowflake = Cortex memo + native feed; aws = Bedrock + Firehose
  IN COMPUTE POOL __COMPUTE_POOL__
  QUERY_WAREHOUSE = __DEMO_WH__
  FROM SPECIFICATION
$$
spec:
  containers:
    - name: app
      image: /__DEMO_DB__/app/images/sg-retail-customer-360-app:v1
      env:
        SNOWFLAKE_DATABASE: __DEMO_DB__
        SNOWFLAKE_SCHEMA: CURATED
        SNOWFLAKE_WAREHOUSE: __DEMO_WH__
        DEMO_PLATFORM: __DEMO_PLATFORM__
      resources:
        requests: {cpu: 0.1, memory: 384M}
        limits: {cpu: 1, memory: 1G}
      readinessProbe: {port: 8080, path: /}
  endpoints:
    - name: app
      port: 8080
      public: true
$$;
