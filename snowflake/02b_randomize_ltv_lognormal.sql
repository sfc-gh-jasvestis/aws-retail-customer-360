-- Apply log-normal customer LTV: 2% whales (25x avg), 8% high-value (8x), 25% above-avg, 40% avg, 25% low.
-- Hash-based deterministic per-customer multiplier with per-transaction jitter.

USE SCHEMA RETAIL_CUSTOMER_360.RAW;

CREATE OR REPLACE TABLE TRANSACTIONS AS
WITH cust_tier AS (
  SELECT CUSTOMER_ID,
    CASE
      WHEN ABS(HASH(CUSTOMER_ID,'tier')) % 1000 < 20  THEN 25.0   -- 2% whales
      WHEN ABS(HASH(CUSTOMER_ID,'tier')) % 1000 < 100 THEN 8.0    -- 8% high-value
      WHEN ABS(HASH(CUSTOMER_ID,'tier')) % 1000 < 350 THEN 2.5    -- 25% above-avg
      WHEN ABS(HASH(CUSTOMER_ID,'tier')) % 1000 < 750 THEN 1.0    -- 40% average
      ELSE 0.3                                                    -- 25% low
    END AS spend_mult
  FROM RETAIL_CUSTOMER_360.RAW.CUSTOMERS
)
SELECT t.TXN_ID, t.CUSTOMER_ID, t.TXN_DATE, t.STORE_ID, t.CHANNEL,
  ROUND(t.TOTAL_AMOUNT * c.spend_mult * (60 + ABS(HASH(t.TXN_ID,'jit'))%81)/100.0, 2) AS TOTAL_AMOUNT,
  t.ITEMS_COUNT, t.PAYMENT_METHOD, t.LOADED_AT
FROM TRANSACTIONS t JOIN cust_tier c ON t.CUSTOMER_ID = c.CUSTOMER_ID;
