# Demo Script: Customer 360 & Loyalty Hub
## 3-Minute Recorded Walkthrough
**Format**: Screen recording with voiceover
**Target**: Customer meeting / booth loop / social share

---

## Two Personas

| Persona | Role | Tool | What they care about |
|---|---|---|---|
| **Marketing Analyst** | Day-to-day operations | Streamlit in Snowflake | Customer profiles, segmentation, churn risk, personalized actions |
| **CMO** | Executive oversight | Amazon QuickSight + Amazon Q | CLV trends, segment health, campaign ROI, churn dashboard |

---

## What's Built

| Layer | Component | Detail |
|---|---|---|
| **RAW** | 7 tables | CUSTOMERS (5K), TRANSACTIONS (100K), LOYALTY_EVENTS (50K), FEEDBACK (10K), TICKETS (5K), CAMPAIGNS (200), RESPONSES (20K) |
| **CURATED** | 3 Dynamic Tables | CUSTOMER_PROFILE (unified 360), CUSTOMER_SEGMENTS, CAMPAIGN_PERFORMANCE |
| **AI** | Cortex Search + Bedrock | Customer insight search (15K docs), Personalized NBA via Cortex/Bedrock |
| **ML** | CLASSIFICATION + FORECAST | Churn prediction (284 at-risk, 7 churned), Revenue forecast (30d by channel) |
| **AWS** | Bedrock + SES + QuickSight | Personalized messages, automated re-engagement, executive dashboards |

---

## Script

### [0:00–0:30] THE PROBLEM & ARCHITECTURE

> "Your marketing team knows who's churning but can't act fast enough. This demo shows Snowflake detecting churn risk with ML, generating personalized re-engagement with Bedrock, and triggering automated emails via SES. All from one platform."

### [0:30–1:00] TAB 1: CUSTOMER 360

> "5,000 customers across 12 APJ markets. Unified profile: lifetime spend, basket size, loyalty points, feedback sentiment — all from Dynamic Tables refreshing every 5 minutes."

**Action**: Search a customer by name, show the full profile.

### [1:00–1:30] TAB 3: CHURN RISK

> "Snowflake ML Classification — every customer scored. 284 at risk, 7 already churned. No Python, no SageMaker. Sort by churn probability."

**Action**: Show the at-risk table sorted by probability.

### [1:30–2:15] TAB 4: PERSONALIZED ACTIONS

> "Now the magic. Select this Gold-tier customer — 92 days since last purchase, lifetime spend $8K. Click Generate NBA."

**Action**: Click "Generate Personalized NBA with Bedrock". Wait for result.

> "Bedrock says: offer 2X loyalty points on their preferred category, free shipping for 30 days. Here's the email preview — personalized, ready to send via SES."

### [2:15–2:40] TAB 5: ASK CUSTOMER

> "And for the questions you haven't thought of yet. 'How many Gold customers have churn risk above 70%?' The Semantic View answers it."

### [2:40–3:00] CLOSE

> "When that churn alert fires, Snowflake doesn't just detect it — it writes the email and sends it. The customer gets a personalized offer 5 minutes after their risk score crosses the threshold."

---

## Key Demo Differentiators (vs Supply Chain)

1. **Amazon Bedrock** — personalized NBA generation (Supply Chain has none)
2. **Amazon SES** — automated churn re-engagement emails
3. **No S3** — first-party customer data stays in Snowflake (no data lake)
4. **ML Classification** — multi-class churn prediction (not forecast/anomaly)
5. **Customer-specific** — segments, CLV, loyalty, feedback sentiment
