# Singapore Retail Customer 360

**Singapore - Omnichannel Retail**
Use case: loyalty cohort retention, service issues, churn and CRM touch controls

> Customer 360 retention monitoring for 48 fictional loyalty cohorts of Kopi Lane Retail, a fictional Singapore omnichannel retailer with malls and an online store serving Orchard, Tampines, Jurong East, Woodlands and Punggol. Cohorts are aggregate member groups; there are no individual customer records. The demo covers dynamic tables, a churn classifier evaluated on a time-based holdout, a service-issue forecast, return rate anomaly detection, a Cortex Agent that cites SOPs, a live engagement feed with an alert, and an SPCS app.

## Why Snowflake

- **Dynamic tables** turn cohort-day rows into purchases, service issues, churned members, unsubscribes and CRM touch compliance; `run_core.py` reconciles them against RAW on every build
- **Churn classification** gives each cohort a next-7-day probability, evaluated on a time-based holdout
- **Service-issue forecast** projects 14 days of retailer-wide service issues with prediction intervals, to plan customer service cover across the five planning areas
- **Grounded AI**: the Cortex Agent (Analyst over a semantic view, Search over SOPs) shows the SQL it ran and the SOPs it cited
- **Live engagement**: a native simulator (Snowflake only) or Firehose, S3 and Snowpipe (AWS build), feeding an alert and email

## What is built

| | |
|---|---|
| Dimension table | `RAW.COHORTS` (48 rows) |
| Fact table | `RAW.COHORT_DAILY` (4,320 cohort-days, 90 days) |
| Curated layer | `CURATED.KPI_SUMMARY`, `PERFORMANCE_SUMMARY`, `ISSUE_SUMMARY`, `TREND_ANALYSIS` |
| ML | `ML.CHURN_RISK_SCORES`, `ML.CHURN_RISK_HOLDOUT_METRICS`, `ML.ISSUE_FORECAST`, `ML.RETURN_RATE_ANOMALIES` |

Currency: SGD. Planning areas: Orchard, Tampines, Jurong East, Woodlands, Punggol.
Segments: Value shoppers, Premium loyalists, Family shoppers, Young professionals, Occasional gifters.

## KPI cards (live from `CURATED.KPI_SUMMARY`; no fallback values)

| Card | Value from the seeded data |
|---|---|
| Issue-Free Purchase Rate | 99.94% |
| Service Issues Raised | 775 |
| Churned Members | 164 |
| Issue Churn Rate | 21.2% |
| Unsubscribes | 79 |
| Revenue (SGD M) | 108 |
| Purchases Made | 1,385,499 |
| CRM Touch Compliance | 73.7% |
| Cohorts Monitored | 48 |
| Profile Completeness | 54.1% |
| Profile Fields Pending | 28 |

Values are synthetic. The data is HASH-seeded, so a rebuild reproduces them; dates are relative to the build day.

## Demo flow

1. Executive Cockpit (Wen Hui Chua, Head of Customer Retention): KPI cards, daily service issues against churned members, issues and churn by issue type, and the cohort table by planning area
2. Predictive (Hafiz Osman, CRM and Loyalty Analyst): holdout metrics, risk bands, the 14-day service-issue forecast and return rate anomalies
3. Controls: CRM touch compliance, profile completeness and pending profile fields, CRM touch compliance against churned members, then the action memo
4. Live Engagement: run `CALL APP.SIMULATE_ENGAGEMENT(20)` (Snowflake only) or `python aws/publish_engagement.py --count 20` (AWS build), then `EXECUTE ALERT APP.LIVE_ENGAGEMENT_ALERT`, and show the alert log and email
5. Ask AI: the Cortex Agent answers metric questions through the semantic view, cites SOPs from Cortex Search and shows its SQL
6. QuickSight (AWS build): the same Snowflake tables through DIRECT_QUERY
7. Architecture: both builds side by side

## Talking points

- 99.94% of purchases go through without a service issue. The 775 service issues are where the retention team spends its time, and 21.2% of them end with members churning.
- Points not credited is the biggest source of churned members (47 of 200 issues). The two mall checkout outages, in Jurong East and Woodlands, hit every cohort in the planning area on one day; all 19 of those issues were resolved with the members retained.
- Woodlands cohorts have the most churned members (66); Tampines and Punggol have the fewest (21 each).
- On a time-based holdout the risk model reaches precision 0.36 and recall 0.28 at 0.5, against a 0.20 base rate. Use it to decide which cohort gets a retention review first, not as a verdict on a cohort.
- Mall checkout outages are left out of model training because the cohort did not cause them.

## Business impact

Use only the sourced references in `README.md` (Business Impact).
