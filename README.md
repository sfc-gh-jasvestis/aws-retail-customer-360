# Customer 360 & Loyalty Hub
### Snowflake + Amazon Bedrock + SES + QuickSight | Retail/CPG

> End-to-end customer intelligence across 12 APJ markets. Snowflake ML detects churn, Amazon Bedrock writes personalized re-engagement offers, Amazon SES delivers the email, Cortex Analyst enables self-serve analytics, and QuickSight powers executive dashboards.

```
Customer Data (first-party) --> Snowflake RAW (5K customers, 100K txns)
                                       |
                    +------------------+
                    v                  v
             Dynamic Tables       Cortex Search
             (5 min refresh)    (15K feedback + tickets)
             |-- CUSTOMER_PROFILE
             |-- CUSTOMER_SEGMENTS
             +-- CAMPAIGN_PERF
                    |
                    v
              Snowflake ML
           +--------+--------+
           v                 v
      CLASSIFICATION      FORECAST
      (churn risk)     (revenue by channel)
           |
           v
    Amazon Bedrock (Claude Sonnet 4.5) --> Personalized NBA
           |
           v
    Amazon SES --> Re-engagement Email
           |
           v
    Streamlit in Snowflake     Amazon QuickSight + Q
    (analyst: 5 tabs)          (executive dashboards + NLP)
           |
           v
    Cortex Analyst via Semantic View --> Natural Language Q&A
```

## What It Does

| Capability | Technology | Detail |
|---|---|---|
| Customer 360 | Dynamic Tables | Unified profile: spend, frequency, recency, tier, loyalty, sentiment |
| Segmentation | CASE rules on DTs | Segments: Champions, Loyal, Potential Loyalist, Needs Attention, At Risk |
| Churn Prediction | Snowflake ML CLASSIFICATION | Multi-class: ACTIVE / AT_RISK / CHURNED (284 at-risk, 7 churned) |
| Revenue Forecast | Snowflake ML FORECAST | 30-day revenue prediction by channel |
| Personalization | Amazon Bedrock (Claude Sonnet 4.5) via EAI | Generates personalized NBA per customer |
| Email Delivery | Amazon SES via EAI | Sends re-engagement emails from Snowflake |
| Insight Search | Cortex Search | Semantic search over 15K feedback + support tickets |
| Analyst UI | Streamlit in Snowflake | 5-tab Customer Hub |
| Executive BI | Amazon QuickSight + Amazon Q | Customer Overview + Campaign Performance dashboards |
| NL Queries | Cortex Analyst + Semantic View | "What is the average lifetime spend by country?" |

## Two Personas

| Persona | Tool | What they see |
|---|---|---|
| **Marketing Analyst** | Streamlit in Snowflake | Customer profiles, segments, churn risk, Bedrock NBA, SES email, Cortex Analyst Q&A |
| **CMO** | Amazon QuickSight + Amazon Q | CLV by segment & country, campaign performance, NLP queries |

## Key AWS Differentiators

This demo showcases the **detect -> personalize -> deliver** loop:
1. **Snowflake ML** detects churn risk (CLASSIFICATION)
2. **Amazon Bedrock** generates a personalized offer (Claude Sonnet 4.5 via EAI)
3. **Amazon SES** sends the re-engagement email (via EAI)
4. **Amazon QuickSight** provides executive dashboards + Amazon Q for NLP

No S3 -- first-party customer data stays in Snowflake's governance perimeter.

## Repo Structure

```
retail-customer-360/
|-- snowflake/
|   |-- 00_setup.sql              # DB, schemas, warehouse
|   +-- 01_integrations.sql       # Bedrock + SES EAIs, network rules, UDFs
|-- streamlit/
|   |-- streamlit_app.py          # 5-tab Customer Hub (source of truth)
|   +-- deploy/                   # Deploy copy + snowflake.yml
|-- quicksight/
|   +-- deploy.sh                 # 2 datasets + Q topic
|-- demo/
|   +-- demo_script.md            # 3-min recorded demo narration
+-- README.md
```

**Note:** SQL files for raw tables (`02_raw_tables.sql`), curated layer (`03_curated.sql`), search (`04_search.sql`), ML (`05_ml.sql`), and semantic view (`08_semantic.sql`) were executed interactively during build. The objects exist in Snowflake but the SQL is not yet extracted to files.

## Data

| Table | Rows | Content |
|---|---|---|
| CUSTOMERS | 5,000 | APJ customers across 12 countries, Gold/Silver/Bronze tiers |
| TRANSACTIONS | 100,000 | Purchase history: In-Store, Online, Mobile, Marketplace |
| LOYALTY_EVENTS | 50,000 | Points earn/redeem/expire events |
| CUSTOMER_FEEDBACK | 10,000 | Reviews with ratings and feedback text |
| SUPPORT_TICKETS | 5,000 | Support cases with descriptions and resolutions |
| CAMPAIGNS | 200 | Marketing campaigns (Email, Push, SMS, In-App, Social) |
| CAMPAIGN_RESPONSES | 20,000 | Open/click/convert/unsubscribe events |

## Streamlit App (5 Tabs)

| Tab | Feature | Technology |
|---|---|---|
| Customer 360 | Unified profile, KPIs, customer search | Dynamic Tables |
| Segmentation | Segment distribution, CLV comparison | DTs + CASE rules |
| Churn Risk | ML predictions, at-risk customer list | Snowflake ML CLASSIFICATION |
| Personalized Actions | Bedrock NBA generation + SES email send | Amazon Bedrock + SES via EAI |
| Ask Customer | Natural language queries with SQL generation | Cortex Analyst + Semantic View |

## Quick Start

### Prerequisites
- Snowflake account with ACCOUNTADMIN
- `snow` CLI configured
- AWS CLI with Bedrock, SES, QuickSight access (us-west-2)

### Deploy
```bash
# 1. Run SQL setup (00_setup.sql, 01_integrations.sql)
# 2. Populate secrets with AWS credentials
ALTER SECRET RETAIL_CUSTOMER_360.AI.BEDROCK_SECRET
    SET SECRET_STRING = '{"aws_access_key_id":"AKIA...","aws_secret_access_key":"..."}';
ALTER SECRET RETAIL_CUSTOMER_360.AI.SES_SECRET
    SET SECRET_STRING = '{"aws_access_key_id":"AKIA...","aws_secret_access_key":"..."}';

# 3. Deploy Streamlit
snow stage copy streamlit/streamlit_app.py @RETAIL_CUSTOMER_360.APP.STREAMLIT_STAGE --overwrite
# Then CREATE STREAMLIT ... (see 01_integrations.sql)

# 4. Deploy QuickSight
bash quicksight/deploy.sh
```

### Health Check
```sql
SELECT
    (SELECT COUNT(*) FROM RETAIL_CUSTOMER_360.RAW.CUSTOMERS) AS customers,
    (SELECT COUNT(*) FROM RETAIL_CUSTOMER_360.RAW.TRANSACTIONS) AS transactions,
    (SELECT COUNT(*) FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE) AS profiles,
    (SELECT COUNT(*) FROM RETAIL_CUSTOMER_360.ML.CHURN_PREDICTIONS) AS predictions;
-- Expected: 5000, 100000, 5000, 5000
```

### Gotchas / Known Issues
- **Bedrock model versions**: Newer Claude models require inference profiles (e.g., `us.anthropic.claude-sonnet-4-5-20250929-v1:0`). Direct model IDs like `anthropic.claude-3-5-sonnet-*` are deprecated.
- **SES sandbox**: In sandbox mode, both sender AND recipient must be verified. For demo, sender and recipient are set to the same verified email.
- **Cortex Analyst in SiS**: Use `_snowflake.send_snow_api_request("POST", "/api/v2/cortex/analyst/message", ...)` -- NOT `_snowflake.send_message()` which doesn't exist.
- **Customer names**: Synthetic data has ~42 duplicate name combinations (e.g., 42 "Wei Chen"). Search by CUSTOMER_ID for unique results.
- **DT segment CASE order**: Recency checks (At Risk, Hibernating) must come BEFORE spend checks (Champions, Loyal) or dormant high-spenders get misclassified.
- **QuickSight datasets**: Use DIRECT_QUERY mode (not SPICE) so dashboards refresh automatically when DTs update.

## Legal

Licensed under the Apache License, Version 2.0.

This is a personal demo project and is **not an official Snowflake offering**. It comes with no support or warranty.
