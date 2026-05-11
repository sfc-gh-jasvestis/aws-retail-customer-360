# Demo Script: Customer 360 & Loyalty Hub
## 3-Minute Recorded Walkthrough
**Format**: Screen recording with voiceover
**Target**: Customer meeting / booth loop / social share

---

## Two Personas

| Persona | Role | Tool | What they care about |
|---|---|---|---|
| **Marketing Analyst** | Day-to-day operations | Streamlit in Snowflake | Customer profiles, segmentation, churn risk, personalized actions |
| **CMO** | Executive oversight | Amazon QuickSight | CLV by segment & country, campaign performance, board-ready visuals |

---

## What's Built

| Layer | Component | Detail |
|---|---|---|
| **RAW** | 7 tables | CUSTOMERS (5K), TRANSACTIONS (100K), LOYALTY_EVENTS (50K), FEEDBACK (10K), TICKETS (5K), CAMPAIGNS (200), RESPONSES (20K) |
| **CURATED** | 3 Dynamic Tables | CUSTOMER_PROFILE (unified 360), CUSTOMER_SEGMENTS, CAMPAIGN_PERFORMANCE |
| **AI** | Cortex Search + Cortex Analyst | Customer insight search (15K docs), Semantic View for natural language analytics |
| **ML** | Segmentation + FORECAST | Risk segmentation (29 At Risk, 165 Needs Attention), Revenue forecast (30d by channel) |
| **AWS** | Bedrock + SES + QuickSight | Bedrock generates personalized NBA, SES delivers emails, QuickSight serves exec dashboards |

---

## The Story

A retail company across 12 APJ markets has a loyalty problem. Customers are churning — and by the time the marketing team notices, it's too late. They need a system that **detects** risk in real time, **writes** the perfect re-engagement message, **sends** it automatically, and lets **executives** see the big picture — all without moving data out of Snowflake.

---

## Script

### [0:00-0:20] THE HOOK

> "What if your data platform could detect a customer about to leave, write them a personalized email, and send it — all before your marketing team finishes their morning coffee? That's what we built. Let me show you."

### [0:20-0:50] TAB 1: CUSTOMER 360

> "Five thousand customers across 12 APJ markets. Every profile is a unified view — lifetime spend, loyalty points, basket size, feedback rating, open tickets — stitched together by Dynamic Tables that refresh every 5 minutes. This isn't a batch report. It's a living, breathing customer record."

**Action**: Search "CUST-00001", show the full profile row.

### [0:50-1:10] TAB 2: SEGMENTATION

> "From that profile, Snowflake automatically segments every customer. Champions, Loyal, Potential Loyalists — and critically — Needs Attention and At Risk. These aren't static labels. They update as behavior changes."

**Action**: Glance at the segment distribution and CLV-by-segment charts.

### [1:10-1:35] TAB 3: CHURN RISK

> "Now here's where it gets interesting. The Dynamic Table scores every single customer in real time — 29 At Risk, 165 Needs Attention. These aren't static segments — they recalculate every 5 minutes based on recency, spend, and engagement. When a Champion goes silent for 90 days, they flip to At Risk automatically."

**Action**: Point out the segment KPI cards. Scroll the at-risk table.

### [1:35-2:20] TAB 4: PERSONALIZED ACTIONS — THE MONEY SHOT

> "This is the part I love. Pick a customer — Mei Lee, Gold tier, Auckland. She hasn't purchased in over 60 days. Her feedback rating is 2 out of 5. Something went wrong. Let's fix it."

**Action**: Select Mei Lee. Review her profile card.

> "One click — Generate NBA with Bedrock. Snowflake calls Amazon Bedrock through an External Access Integration. Claude analyzes her profile and writes a personalized re-engagement strategy — the offer, the urgency, even the email copy."

**Action**: Click "Generate Personalized NBA with Bedrock". Wait 3-5 seconds.

> "High urgency. A $50 voucher, bonus loyalty points, and a personal call from the Auckland store manager. And here's the email — ready to send."

**Action**: Point at the email preview.

> "Now watch this. Send it."

**Action**: Click "Send Re-engagement Email via SES".

> "Amazon SES just delivered that email. Snowflake detected the risk, Bedrock wrote the message, SES sent it. The customer data never left Snowflake's governance boundary until that email went out."

### [2:20-2:40] TAB 5: ASK CUSTOMER

> "And for the CMO who wants to explore on their own — Cortex Analyst. Natural language to SQL, powered by the Semantic View. 'What is the average lifetime spend by country?' — instant answer, no SQL required."

**Action**: Click the sample question. Show the result table.

### [2:40-3:00] QUICKSIGHT + CLOSE

> "And for the board meeting? The CMO doesn't open Streamlit — they open Amazon QuickSight. Same data, same Dynamic Tables, executive-ready visuals."

**Action**: Switch to QuickSight tab. Show Customer Overview dashboard (Customers by Segment + CLV by Tier and Country).

> "But the CMO also wants to explore. Watch this — Amazon Q."

**Action**: Open the Q bar and type: **"What is the average lifetime spend by segment?"**

> "Natural language, instant answer — powered by the same curated layer in Snowflake. Two personas, two tools, one source of truth."

**Action**: Show the Q result. Briefly click to Campaign Performance tab.

> "One data platform. Five capabilities. Detect, score, generate, deliver, explore. That's Snowflake and AWS — better together."

---

## Key Demo Differentiators (vs Supply Chain)

1. **Amazon Bedrock** — personalized NBA generation via External Access Integration (Claude Sonnet 4.5)
2. **Amazon SES** — automated churn re-engagement emails triggered from Snowflake
3. **Amazon QuickSight** — executive dashboards for the CMO persona (Customer Overview + Campaign Performance)
4. **Cortex Analyst** — self-serve natural language analytics via Semantic View
5. **Real-time segmentation** — Dynamic Table recalculates risk segments every 5 minutes based on live behavior
6. **No S3** — first-party customer data stays in Snowflake (no data lake export)
7. **End-to-end orchestration** — detect, generate, deliver, explore — one platform

---

## Demo Prep Checklist

- [ ] Streamlit app loaded and on Tab 1
- [ ] QuickSight dashboard open in separate browser tab
- [ ] Test Bedrock UDF works: `SELECT RETAIL_CUSTOMER_360.AI.BEDROCK_GENERATE_NBA('Say hello')`
- [ ] Clear `last_nba` session state (refresh the app)
- [ ] Pre-select Mei Lee (CUST-01881) for Tab 4 walkthrough
