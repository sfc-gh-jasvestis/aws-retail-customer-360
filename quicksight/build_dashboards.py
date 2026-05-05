#!/usr/bin/env python3
"""Build/refresh QuickSight datasets + dashboards + Q topics for all 16 demos.
Reuses snowflake-demos-ds, applies snowflake-demo-theme, 4 KPI + 2 chart layout."""
import json
import subprocess
import sys
import uuid
import argparse

ACCOUNT = "__AWS_ACCOUNT_ID__"
REGION = "us-west-2"
DS_ARN = f"arn:aws:quicksight:{REGION}:{ACCOUNT}:datasource/snowflake-demos-ds"
THEME_ARN = f"arn:aws:quicksight:{REGION}:{ACCOUNT}:theme/snowflake-demo-theme"
PRINCIPAL = f"arn:aws:quicksight:{REGION}:{ACCOUNT}:user/default/{ACCOUNT}"

DATASET_PERMS = [{
    "Principal": PRINCIPAL,
    "Actions": [
        "quicksight:DescribeDataSet", "quicksight:DescribeDataSetPermissions",
        "quicksight:PassDataSet", "quicksight:DescribeIngestion",
        "quicksight:ListIngestions", "quicksight:UpdateDataSet",
        "quicksight:DeleteDataSet", "quicksight:CreateIngestion",
        "quicksight:CancelIngestion", "quicksight:UpdateDataSetPermissions",
    ]
}]

DASH_PERMS = [{
    "Principal": PRINCIPAL,
    "Actions": [
        "quicksight:DescribeDashboard", "quicksight:ListDashboardVersions",
        "quicksight:UpdateDashboardPermissions", "quicksight:QueryDashboard",
        "quicksight:UpdateDashboard", "quicksight:DeleteDashboard",
        "quicksight:DescribeDashboardPermissions", "quicksight:UpdateDashboardPublishedVersion",
    ]
}]

TOPIC_PERMS = [{
    "Principal": PRINCIPAL,
    "Actions": [
        "quicksight:DescribeTopic", "quicksight:DescribeTopicRefreshSchedule",
        "quicksight:DeleteTopic", "quicksight:UpdateTopicPermissions", "quicksight:CreateTopicRefreshSchedule",
        "quicksight:DeleteTopicRefreshSchedule", "quicksight:ListTopicRefreshSchedules",
        "quicksight:UpdateTopicRefreshSchedule", "quicksight:DescribeTopicPermissions", "quicksight:UpdateTopic",
        "quicksight:DescribeTopicRefresh"
    ]
}]


# 16 demo configs
DEMOS = [
    # (id_suffix, name, sql, kpis, charts, q_questions, ds_id)
    {
        "id": "supply-chain", "name": "Supply Chain Command Center",
        "sql": """SELECT CARRIER_NAME, STATUS, COMMODITY_TYPE, ORIGIN_PORT_NAME,
       VALUE_USD::FLOAT AS VALUE_USD, DAYS_DELAYED::INT AS DAYS_DELAYED,
       IMPACT_SCORE::FLOAT AS IMPACT_SCORE, CONTAINER_COUNT::INT AS CONTAINER_COUNT,
       SHIPMENT_ID
FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS""",
        "ds_id": "mfg-supply-chain",
        "ds_name": "MFG: Supply Chain",
        "kpis": [
            {"label": "Total Shipments", "field": "SHIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Stuck", "field": "SHIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "STUCK")},
            {"label": "Delayed", "field": "SHIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "DELAYED")},
            {"label": "Total Value $M", "field": "VALUE_USD", "agg": "SUM", "type": "decimal", "scale": 1e6},
        ],
        "charts": [
            {"type": "bar", "title": "Top 10 Carriers by Shipment Count",
             "x": ("CARRIER_NAME", "string"), "y": ("SHIPMENT_ID", "string", "DISTINCT_COUNT"),
             "color": ("STATUS", "string"), "topn": 10},
            {"type": "donut", "title": "Shipments by Status",
             "category": ("STATUS", "string"), "value": ("SHIPMENT_ID", "string", "DISTINCT_COUNT")},
        ],
        "q": ["How many shipments are stuck?", "Which carrier has the most delayed shipments?", "What is the total value of stuck shipments?"],
        "topic_id": "mfg-supply-chain-q", "topic_name": "Supply Chain Command Center",
        "dashboard_id": "mfg-supply-chain-dashboard",
        "dashboard_name": "Supply Chain Command Center",
        "drop_existing": True,
    },
    {
        "id": "demand", "name": "Demand Forecast Optimization",
        "sql": """SELECT ih.PRODUCT_ID, ih.PRODUCT_NAME, ih.CATEGORY, ih.WAREHOUSE_NAME,
       ih.AVG_ON_HAND::INT AS AVG_ON_HAND, ih.DAYS_OF_SUPPLY::FLOAT AS DAYS_OF_SUPPLY,
       ih.RISK_LEVEL, ih.VALUE_AT_RISK::FLOAT AS VALUE_AT_RISK
FROM MANUFACTURING_DEMAND.CURATED.INVENTORY_HEALTH ih""",
        "ds_id": "mfg-demand",
        "ds_name": "MFG: Demand",
        "kpis": [
            {"label": "Total SKUs", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Stockout SKUs", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("RISK_LEVEL", "STOCKOUT")},
            {"label": "Overstock SKUs", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("RISK_LEVEL", "OVERSTOCK")},
            {"label": "Value at Risk $M", "field": "VALUE_AT_RISK", "agg": "SUM", "type": "decimal", "scale": 1e6},
        ],
        "charts": [
            {"type": "donut", "title": "Inventory Risk Distribution",
             "category": ("RISK_LEVEL", "string"), "value": ("PRODUCT_ID", "string", "DISTINCT_COUNT")},
            {"type": "bar", "title": "Value at Risk by Category",
             "x": ("CATEGORY", "string"), "y": ("VALUE_AT_RISK", "decimal", "SUM"),
             "color": ("RISK_LEVEL", "string")},
        ],
        "q": ["How many SKUs are at stockout risk?", "Which category has the highest value at risk?", "How many SKUs are overstocked?"],
        "topic_id": "mfg-demand-q", "topic_name": "Demand Forecast Optimization",
        "dashboard_id": "mfg-demand-dashboard",
        "dashboard_name": "Demand Forecast Optimization",
        "drop_existing": True,
    },
    {
        "id": "port-ops", "name": "Port Operations Monitor",
        "sql": """SELECT TERMINAL_NAME, OPERATOR, BERTHS::INT AS BERTHS,
       VESSELS_BERTHED::INT AS VESSELS_BERTHED, FREE_BERTHS::INT AS FREE_BERTHS,
       QUEUE_DEPTH::INT AS QUEUE_DEPTH, UTILIZATION_PCT::FLOAT AS UTILIZATION_PCT,
       AVG_WAIT_HOURS::FLOAT AS AVG_WAIT_HOURS, CRANE_COUNT::INT AS CRANE_COUNT,
       MAX_TEU_PER_DAY::INT AS MAX_TEU_PER_DAY
FROM MANUFACTURING_PORT_OPS.CURATED.TERMINAL_STATUS""",
        "ds_id": "mfg-port-ops",
        "ds_name": "MFG: Port Ops",
        "kpis": [
            {"label": "Terminals", "field": "TERMINAL_NAME", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Vessels Berthed", "field": "VESSELS_BERTHED", "agg": "SUM", "type": "decimal"},
            {"label": "Vessels in Queue", "field": "QUEUE_DEPTH", "agg": "SUM", "type": "decimal"},
            {"label": "Avg Utilization %", "field": "UTILIZATION_PCT", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Utilization % by Terminal",
             "x": ("TERMINAL_NAME", "string"), "y": ("UTILIZATION_PCT", "decimal", "AVERAGE")},
            {"type": "bar", "title": "Avg Wait Hours by Terminal",
             "x": ("TERMINAL_NAME", "string"), "y": ("AVG_WAIT_HOURS", "decimal", "AVERAGE")},
        ],
        "q": ["Which terminal has the longest wait?", "How many vessels are waiting?", "What is the avg utilization?"],
        "topic_id": "mfg-port-ops-q", "topic_name": "Port Operations Monitor",
        "dashboard_id": "mfg-port-ops-dashboard",
        "dashboard_name": "Port Operations Monitor",
        "drop_existing": True,
    },
    {
        "id": "maintenance", "name": "Predictive Maintenance",
        "sql": """SELECT EQUIPMENT_ID, NAME AS EQUIPMENT_NAME, EQUIPMENT_TYPE, LOCATION,
       STATUS, CRITICALITY, HEALTH_SCORE::FLOAT AS HEALTH_SCORE,
       CRITICAL_SENSORS::INT AS CRITICAL_SENSORS, WARNING_SENSORS::INT AS WARNING_SENSORS
FROM MANUFACTURING_MAINTENANCE.CURATED.EQUIPMENT_HEALTH""",
        "ds_id": "mfg-maintenance",
        "ds_name": "MFG: Maintenance",
        "kpis": [
            {"label": "Total Equipment", "field": "EQUIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Critical", "field": "EQUIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "CRITICAL")},
            {"label": "Warning", "field": "EQUIPMENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "WARNING")},
            {"label": "Avg Health Score", "field": "HEALTH_SCORE", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "donut", "title": "Equipment Status Distribution",
             "category": ("STATUS", "string"), "value": ("EQUIPMENT_ID", "string", "DISTINCT_COUNT")},
            {"type": "bar", "title": "Avg Health Score by Equipment Type",
             "x": ("EQUIPMENT_TYPE", "string"), "y": ("HEALTH_SCORE", "decimal", "AVERAGE"),
             "color": ("STATUS", "string")},
        ],
        "q": ["Which equipment is critical?", "What is the avg health by type?", "How many warnings are active?"],
        "topic_id": "mfg-maintenance-q", "topic_name": "Predictive Maintenance",
        "dashboard_id": "mfg-maintenance-dashboard",
        "dashboard_name": "Predictive Maintenance",
        "drop_existing": True,
    },
    {
        "id": "fsi-regulatory", "name": "FSI Regulatory Compliance",
        "sql": """SELECT EVENT_ID, EVENT_TYPE, SEVERITY, STATUS,
       EMPLOYEE_NAME, DESCRIPTION,
       EVENT_TS::TIMESTAMP AS EVENT_TS
FROM FSI_REGULATORY_COMPLIANCE.CURATED.COMPLIANCE_EVENTS""",
        "ds_id": "fsi-regulatory-events",
        "ds_name": "FSI: Compliance Events",
        "kpis": [
            {"label": "Total Events", "field": "EVENT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "High Severity", "field": "EVENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("SEVERITY", "HIGH")},
            {"label": "Open", "field": "EVENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "OPEN")},
            {"label": "Employees Flagged", "field": "EMPLOYEE_NAME", "agg": "DISTINCT_COUNT", "type": "string"},
        ],
        "charts": [
            {"type": "bar", "title": "Events by Type",
             "x": ("EVENT_TYPE", "string"), "y": ("EVENT_ID", "string", "DISTINCT_COUNT"),
             "color": ("SEVERITY", "string")},
            {"type": "donut", "title": "Status Distribution",
             "category": ("STATUS", "string"), "value": ("EVENT_ID", "string", "DISTINCT_COUNT")},
        ],
        "q": ["How many high severity events?", "Which regulation area has the most events?", "How many events are open?"],
        "topic_id": "fsi-regulatory-q", "topic_name": "FSI Regulatory Compliance",
        "dashboard_id": "fsi-regulatory-dashboard",
        "dashboard_name": "FSI Regulatory Compliance",
        "drop_existing": False,
    },
    {
        "id": "fsi-payments", "name": "FSI Payments Hub",
        "sql": """SELECT PAYMENT_ID, CORRIDOR, SETTLEMENT_STATUS, CURRENCY,
       AMOUNT_SGD::FLOAT AS AMOUNT_SGD,
       SETTLEMENT_LATENCY_SECONDS::FLOAT AS SETTLEMENT_LATENCY_SECONDS,
       SLA_STATUS, PAYMENT_TYPE
FROM FSI_PAYMENTS.CURATED.PAYMENT_ENRICHED""",
        "ds_id": "fsi-payments-enriched",
        "ds_name": "FSI: Payments",
        "kpis": [
            {"label": "Total Payments", "field": "PAYMENT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Total Volume SGD M", "field": "AMOUNT_SGD", "agg": "SUM", "type": "decimal", "scale": 1e6},
            {"label": "SLA Breaches", "field": "PAYMENT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("SLA_STATUS", "BREACHED")},
            {"label": "Avg Latency (s)", "field": "SETTLEMENT_LATENCY_SECONDS", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Volume by Corridor",
             "x": ("CORRIDOR", "string"), "y": ("AMOUNT_SGD", "decimal", "SUM")},
            {"type": "donut", "title": "Status Distribution",
             "category": ("SETTLEMENT_STATUS", "string"), "value": ("PAYMENT_ID", "string", "DISTINCT_COUNT")},
        ],
        "q": ["What is the total payment volume?", "Which corridor has the most exceptions?", "How many payments are exceptions?"],
        "topic_id": "fsi-payments-q", "topic_name": "FSI Payments Hub",
        "dashboard_id": "fsi-payments-dashboard",
        "dashboard_name": "FSI Payments Hub",
        "drop_existing": False,
    },
    {
        "id": "retail-supply-chain", "name": "Retail Supply Chain",
        "sql": """SELECT PRODUCT_ID, PRODUCT_NAME, CATEGORY, WAREHOUSE_NAME,
       QUANTITY_ON_HAND::INT AS QUANTITY_ON_HAND,
       DAYS_OF_SUPPLY::FLOAT AS DAYS_OF_SUPPLY,
       INVENTORY_STATUS, INVENTORY_VALUE::FLOAT AS INVENTORY_VALUE,
       SUPPLIER_NAME, ALERT_SEVERITY
FROM RETAIL_SUPPLY_CHAIN.CURATED.INVENTORY_HEALTH""",
        "ds_id": "retail-supply-chain-inventory",
        "ds_name": "Retail: Inventory Health",
        "kpis": [
            {"label": "Total SKUs", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Stockouts", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("INVENTORY_STATUS", "Stockout Risk")},
            {"label": "Healthy", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("INVENTORY_STATUS", "Healthy")},
            {"label": "Inventory Value $M", "field": "INVENTORY_VALUE", "agg": "SUM", "type": "decimal", "scale": 1e6},
        ],
        "charts": [
            {"type": "donut", "title": "Inventory Status",
             "category": ("INVENTORY_STATUS", "string"), "value": ("PRODUCT_ID", "string", "DISTINCT_COUNT")},
            {"type": "bar", "title": "Inventory Value by Category",
             "x": ("CATEGORY", "string"), "y": ("INVENTORY_VALUE", "decimal", "SUM")},
        ],
        "q": ["How many SKUs are at stockout risk?", "What is total value at risk?", "Which category has the most stockouts?"],
        "topic_id": "retail-supply-chain-q", "topic_name": "Retail Supply Chain",
        "dashboard_id": "retail-supply-chain-dashboard",
        "dashboard_name": "Retail Supply Chain",
        "drop_existing": False,
    },
    {
        "id": "retail-customer-360", "name": "Retail Customer 360",
        "sql": """SELECT CUSTOMER_ID, FIRST_NAME, LAST_NAME, TIER, CUSTOMER_SEGMENT,
       LIFETIME_SPEND::FLOAT AS LIFETIME_SPEND,
       TXN_COUNT::INT AS TXN_COUNT,
       DAYS_SINCE_LAST_TXN::INT AS DAYS_SINCE_LAST_TXN,
       AVG_FEEDBACK_RATING::FLOAT AS AVG_FEEDBACK_RATING,
       LOYALTY_POINTS::INT AS LOYALTY_POINTS,
       PREFERRED_CHANNEL, COUNTRY
FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE""",
        "ds_id": "retail-customer-profile",
        "ds_name": "Retail: Customer Profile",
        "kpis": [
            {"label": "Customers", "field": "CUSTOMER_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Champions", "field": "CUSTOMER_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("CUSTOMER_SEGMENT", "Champions")},
            {"label": "At Risk", "field": "CUSTOMER_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("CUSTOMER_SEGMENT", "At Risk")},
            {"label": "Avg Lifetime Spend", "field": "LIFETIME_SPEND", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "donut", "title": "Segment Distribution",
             "category": ("CUSTOMER_SEGMENT", "string"), "value": ("CUSTOMER_ID", "string", "DISTINCT_COUNT")},
            {"type": "bar", "title": "Avg Lifetime Spend by Tier",
             "x": ("TIER", "string"), "y": ("LIFETIME_SPEND", "decimal", "AVERAGE")},
        ],
        "q": ["How many at-risk customers?", "What is the avg LTV by tier?", "How many champions do we have?"],
        "topic_id": "retail-customer-360-q", "topic_name": "Retail Customer 360",
        "dashboard_id": "retail-customer-360-dashboard",
        "dashboard_name": "Retail Customer 360",
        "drop_existing": False,
    },
    {
        "id": "retail-merchandising", "name": "Retail Merchandising",
        "sql": """SELECT PRODUCT_ID, PRODUCT_NAME, CATEGORY, SUB_CATEGORY, BRAND,
       AVG_SELLING_PRICE::FLOAT AS AVG_SELLING_PRICE,
       GROSS_MARGIN_PCT::FLOAT AS GROSS_MARGIN_PCT,
       TOTAL_REVENUE::FLOAT AS TOTAL_REVENUE,
       TOTAL_QUANTITY::INT AS TOTAL_QUANTITY,
       AVG_DISCOUNT_PCT::FLOAT AS AVG_DISCOUNT_PCT
FROM RETAIL_MERCHANDISING.CURATED.PRODUCT_MARGIN_ANALYSIS""",
        "ds_id": "retail-merch-margin",
        "ds_name": "Retail: Margin Analysis",
        "kpis": [
            {"label": "Products", "field": "PRODUCT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Avg Margin %", "field": "GROSS_MARGIN_PCT", "agg": "AVERAGE", "type": "decimal"},
            {"label": "Total Revenue $M", "field": "TOTAL_REVENUE", "agg": "SUM", "type": "decimal", "scale": 1e6},
            {"label": "Units Sold", "field": "TOTAL_QUANTITY", "agg": "SUM", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Revenue by Category",
             "x": ("CATEGORY", "string"), "y": ("TOTAL_REVENUE", "decimal", "SUM")},
            {"type": "bar", "title": "Avg Gross Margin % by Category",
             "x": ("CATEGORY", "string"), "y": ("GROSS_MARGIN_PCT", "decimal", "AVERAGE")},
        ],
        "q": ["Which category has the highest revenue?", "What is the avg margin?", "Which brand sells the most units?"],
        "topic_id": "retail-merchandising-q", "topic_name": "Retail Merchandising",
        "dashboard_id": "retail-merchandising-dashboard",
        "dashboard_name": "Retail Merchandising",
        "drop_existing": False,
    },
    {
        "id": "retail-omnichannel", "name": "Retail Omnichannel",
        "sql": """SELECT CHANNEL_NAME, ORDER_DATE,
       ORDER_COUNT::INT AS ORDER_COUNT,
       REVENUE::FLOAT AS REVENUE,
       AOV::FLOAT AS AOV,
       AVG_ITEMS::FLOAT AS AVG_ITEMS
FROM RETAIL_OMNICHANNEL.CURATED.CHANNEL_PERFORMANCE""",
        "ds_id": "retail-omni-channel",
        "ds_name": "Retail: Omnichannel",
        "kpis": [
            {"label": "Total Orders", "field": "ORDER_COUNT", "agg": "SUM", "type": "decimal"},
            {"label": "Total Revenue $M", "field": "REVENUE", "agg": "SUM", "type": "decimal", "scale": 1e6},
            {"label": "Avg Order Value", "field": "AOV", "agg": "AVERAGE", "type": "decimal"},
            {"label": "Avg Items per Order", "field": "AVG_ITEMS", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "donut", "title": "Revenue by Channel",
             "category": ("CHANNEL_NAME", "string"), "value": ("REVENUE", "decimal", "SUM")},
            {"type": "bar", "title": "AOV by Channel",
             "x": ("CHANNEL_NAME", "string"), "y": ("AOV", "decimal", "AVERAGE")},
        ],
        "q": ["Which channel has the highest revenue?", "What is the avg order value by channel?", "Which channel has the lowest conversion?"],
        "topic_id": "retail-omnichannel-q", "topic_name": "Retail Omnichannel",
        "dashboard_id": "retail-omnichannel-dashboard",
        "dashboard_name": "Retail Omnichannel",
        "drop_existing": False,
    },
    {
        "id": "insurance-apj", "name": "Insurance APJ Claims",
        "sql": """SELECT CLAIM_ID, CLAIM_TYPE, POLICY_TYPE, COUNTRY, STATUS,
       CLAIM_AMOUNT::FLOAT AS CLAIM_AMOUNT,
       AI_DECISION, COVERAGE_LIMIT::FLOAT AS COVERAGE_LIMIT,
       PREMIUM::FLOAT AS PREMIUM, CITY
FROM INSURANCE_DEMO_DB.CURATED.CLAIMS""",
        "ds_id": "insurance-claims",
        "ds_name": "Insurance: APJ Claims",
        "kpis": [
            {"label": "Total Claims", "field": "CLAIM_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Pending", "field": "CLAIM_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "Pending")},
            {"label": "Total Amount $M", "field": "CLAIM_AMOUNT", "agg": "SUM", "type": "decimal", "scale": 1e6},
            {"label": "Avg Premium", "field": "PREMIUM", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Claims by Country",
             "x": ("COUNTRY", "string"), "y": ("CLAIM_ID", "string", "DISTINCT_COUNT"),
             "color": ("CLAIM_TYPE", "string")},
            {"type": "donut", "title": "Policy Type Mix",
             "category": ("POLICY_TYPE", "string"), "value": ("CLAIM_ID", "string", "DISTINCT_COUNT")},
        ],
        "q": ["How many claims are pending?", "Which country has the most claims?", "What is the average claim amount?"],
        "topic_id": "insurance-apj-q", "topic_name": "Insurance APJ Claims",
        "dashboard_id": "insurance-apj-dashboard",
        "dashboard_name": "Insurance APJ Claims",
        "drop_existing": False,
    },
    {
        "id": "crypto-surveillance", "name": "Crypto Surveillance",
        "sql": """SELECT ALERT_ID, ALERT_TYPE, SEVERITY, STATUS,
       DETECTED_AT::TIMESTAMP AS DETECTED_AT,
       ML_FRAUD_PROBABILITY::FLOAT AS ML_FRAUD_PROBABILITY,
       COMPOSITE_RISK_TIER, ENTITY_ID, REASON
FROM CRYPTO_SURVEILLANCE.ANALYTICS.ALERTS""",
        "ds_id": "crypto-alerts",
        "ds_name": "Crypto: Alerts",
        "kpis": [
            {"label": "Total Alerts", "field": "ALERT_ID", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Critical", "field": "ALERT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("SEVERITY", "CRITICAL")},
            {"label": "Open", "field": "ALERT_ID", "agg": "DISTINCT_COUNT", "type": "string", "filter": ("STATUS", "OPEN")},
            {"label": "Avg Fraud Probability", "field": "ML_FRAUD_PROBABILITY", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Alerts by Type",
             "x": ("ALERT_TYPE", "string"), "y": ("ALERT_ID", "string", "DISTINCT_COUNT"),
             "color": ("SEVERITY", "string")},
            {"type": "donut", "title": "Status Distribution",
             "category": ("STATUS", "string"), "value": ("ALERT_ID", "string", "DISTINCT_COUNT")},
        ],
        "q": ["How many critical alerts?", "Which alert type is most common?", "How many open cases?"],
        "topic_id": "crypto-surveillance-q", "topic_name": "Crypto Surveillance",
        "dashboard_id": "crypto-surveillance-dashboard",
        "dashboard_name": "Crypto Surveillance",
        "drop_existing": False,
    },
    # Healthcare 4 — already exist, just enrich
    {
        "id": "hc-trials", "name": "Clinical Trials",
        "sql": """SELECT SITE_NAME, COUNTRY, CITY,
       ENROLLMENT_RATE_PCT::FLOAT AS ENROLLMENT_RATE_PCT,
       SCREEN_FAIL_PCT::FLOAT AS SCREEN_FAIL_PCT,
       RETENTION_RATE::FLOAT AS RETENTION_RATE,
       ENROLLMENT_COUNT::INT AS ENROLLMENT_COUNT,
       TARGET_ENROLLMENT::INT AS TARGET_ENROLLMENT,
       AVG_DAYS_TO_ENROLL::FLOAT AS AVG_DAYS_TO_ENROLL,
       TRIAL_TITLE
FROM HEALTHCARE_CLINICAL_TRIALS.CURATED.SITE_PERFORMANCE""",
        "ds_id": "hc-trials-sites",
        "ds_name": "HC: Trial Sites",
        "kpis": [
            {"label": "Sites", "field": "SITE_NAME", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Avg Enrollment %", "field": "ENROLLMENT_RATE_PCT", "agg": "AVERAGE", "type": "decimal"},
            {"label": "Avg Screen Fail %", "field": "SCREEN_FAIL_PCT", "agg": "AVERAGE", "type": "decimal"},
            {"label": "Avg Retention", "field": "RETENTION_RATE", "agg": "AVERAGE", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Enrollment % by Site",
             "x": ("SITE_NAME", "string"), "y": ("ENROLLMENT_RATE_PCT", "decimal", "AVERAGE")},
            {"type": "donut", "title": "Sites by Country",
             "category": ("COUNTRY", "string"), "value": ("SITE_NAME", "string", "DISTINCT_COUNT")},
        ],
        "q": ["Which sites are top performers?", "What is the avg enrollment?", "How many sites by tier?"],
        "topic_id": "hc-clinical-trials-q", "topic_name": "Clinical Trials Intelligence",
        "dashboard_id": "hc-trials-dashboard",
        "dashboard_name": "Clinical Trials: Site Performance",
        "drop_existing": True,
    },
    {
        "id": "hc-radiology", "name": "Radiology TAT",
        "sql": """SELECT MODALITY, METRIC_DATE,
       AVG_TAT_MINUTES::FLOAT AS AVG_TAT_MINUTES,
       STUDIES_COMPLETED::INT AS STUDIES_COMPLETED,
       TAT_SLA_BREACH_COUNT::INT AS TAT_SLA_BREACH_COUNT
FROM HEALTHCARE_RADIOLOGY.CURATED.TAT_METRICS""",
        "ds_id": "hc-radiology-tat",
        "ds_name": "HC: Radiology TAT",
        "kpis": [
            {"label": "Studies", "field": "STUDIES_COMPLETED", "agg": "SUM", "type": "decimal"},
            {"label": "Avg TAT (min)", "field": "AVG_TAT_MINUTES", "agg": "AVERAGE", "type": "decimal"},
            {"label": "SLA Breaches", "field": "TAT_SLA_BREACH_COUNT", "agg": "SUM", "type": "decimal"},
            {"label": "Modalities", "field": "MODALITY", "agg": "DISTINCT_COUNT", "type": "string"},
        ],
        "charts": [
            {"type": "bar", "title": "Avg TAT by Modality",
             "x": ("MODALITY", "string"), "y": ("AVG_TAT_MINUTES", "decimal", "AVERAGE")},
            {"type": "bar", "title": "SLA Breaches by Modality",
             "x": ("MODALITY", "string"), "y": ("TAT_SLA_BREACH_COUNT", "decimal", "SUM")},
        ],
        "q": ["Which modalities are breaching SLA?", "What is the avg TAT?", "How many studies completed?"],
        "topic_id": "hc-radiology-q", "topic_name": "Radiology Analytics",
        "dashboard_id": "hc-radiology-dashboard",
        "dashboard_name": "Radiology: TAT & Critical Findings",
        "drop_existing": True,
    },
    {
        "id": "hc-genomics", "name": "Genomics Variants",
        "sql": """SELECT GENE, CLINICAL_SIGNIFICANCE, PATIENT_COUNT::INT AS PATIENT_COUNT,
       AVG_ALLELE_FREQUENCY::FLOAT AS AVG_ALLELE_FREQUENCY,
       VARIANT_COUNT::INT AS VARIANT_COUNT,
       PATHOGENIC_COUNT::INT AS PATHOGENIC_COUNT,
       AVG_DEPTH::FLOAT AS AVG_DEPTH, COHORT_ID
FROM HEALTHCARE_GENOMICS.CURATED.VARIANT_SUMMARY""",
        "ds_id": "hc-genomics-variants",
        "ds_name": "HC: Variants",
        "kpis": [
            {"label": "Genes", "field": "GENE", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Patients", "field": "PATIENT_COUNT", "agg": "SUM", "type": "decimal"},
            {"label": "Variants", "field": "VARIANT_COUNT", "agg": "SUM", "type": "decimal"},
            {"label": "Pathogenic", "field": "PATHOGENIC_COUNT", "agg": "SUM", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Variant Count by Gene",
             "x": ("GENE", "string"), "y": ("VARIANT_COUNT", "decimal", "SUM"),
             "color": ("CLINICAL_SIGNIFICANCE", "string")},
            {"type": "donut", "title": "Clinical Significance",
             "category": ("CLINICAL_SIGNIFICANCE", "string"), "value": ("VARIANT_COUNT", "decimal", "SUM")},
        ],
        "q": ["Which gene has the most variants?", "How many pathogenic variants?", "What is the avg allele frequency?"],
        "topic_id": "hc-genomics-q", "topic_name": "Genomics Research",
        "dashboard_id": "hc-genomics-dashboard",
        "dashboard_name": "Genomics: Variant Analysis",
        "drop_existing": True,
    },
    {
        "id": "hc-integration", "name": "Population Health Quality",
        "sql": """SELECT MEASURE_NAME, MEASURE_TYPE,
       COMPLIANCE_PCT::FLOAT AS COMPLIANCE_PCT,
       TARGET_PCT::FLOAT AS TARGET_PCT,
       GAP_COUNT::INT AS GAP_COUNT,
       NUMERATOR::INT AS NUMERATOR,
       DENOMINATOR::INT AS DENOMINATOR
FROM HEALTHCARE_INTEGRATION.CURATED.QUALITY_MEASURE_COMPLIANCE
WHERE COMPLIANCE_PCT IS NOT NULL""",
        "ds_id": "hc-integration-quality",
        "ds_name": "HC: Quality Measures",
        "kpis": [
            {"label": "Measures", "field": "MEASURE_NAME", "agg": "DISTINCT_COUNT", "type": "string"},
            {"label": "Avg Compliance %", "field": "COMPLIANCE_PCT", "agg": "AVERAGE", "type": "decimal"},
            {"label": "Total Gaps", "field": "GAP_COUNT", "agg": "SUM", "type": "decimal"},
            {"label": "Patients", "field": "DENOMINATOR", "agg": "SUM", "type": "decimal"},
        ],
        "charts": [
            {"type": "bar", "title": "Compliance % by Measure",
             "x": ("MEASURE_NAME", "string"), "y": ("COMPLIANCE_PCT", "decimal", "AVERAGE")},
            {"type": "bar", "title": "Care Gaps by Measure",
             "x": ("MEASURE_NAME", "string"), "y": ("GAP_COUNT", "decimal", "SUM")},
        ],
        "q": ["Which measures are below 80% compliance?", "What is total care gaps?", "Which measure has the most patients?"],
        "topic_id": "hc-integration-q", "topic_name": "Population Health & Integration",
        "dashboard_id": "hc-integration-dashboard",
        "dashboard_name": "Population Health: Quality & Care Gaps",
        "drop_existing": True,
    },
]


def aws(svc, op, **kw):
    """Run AWS CLI command."""
    cmd = ["aws", svc, op, "--region", REGION, "--aws-account-id", ACCOUNT]
    for k, v in kw.items():
        cmd.append(f"--{k.replace('_', '-')}")
        cmd.append(v)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def col_def(name, type_):
    return {"Name": name, "Type": type_.upper()}


def build_dataset(d):
    cols = []
    seen = set()

    def add(name, type_):
        if name not in seen:
            cols.append(col_def(name, type_))
            seen.add(name)

    for k in d["kpis"]:
        if "field" in k:
            t = k.get("type", "string")
            qst = "DECIMAL" if t == "decimal" else ("INTEGER" if t == "integer" else "STRING")
            add(k["field"], qst)
        if "filter" in k:
            add(k["filter"][0], "STRING")
        if "filter_bool" in k:
            add(k["filter_bool"][0], "BOOLEAN" if False else "STRING")
    for c in d["charts"]:
        if c["type"] == "bar":
            add(c["x"][0], "STRING" if c["x"][1] == "string" else "DECIMAL")
            add(c["y"][0], "STRING" if c["y"][1] == "string" else "DECIMAL")
            if "color" in c:
                add(c["color"][0], "STRING" if c["color"][1] == "string" else "DECIMAL")
        else:  # donut
            add(c["category"][0], "STRING" if c["category"][1] == "string" else "DECIMAL")
            add(c["value"][0], "STRING" if c["value"][1] == "string" else "DECIMAL")

    physical = {
        "PhysicalTableMap": {
            "t1": {
                "CustomSql": {
                    "DataSourceArn": DS_ARN,
                    "Name": d["ds_id"],
                    "SqlQuery": d["sql"],
                    "Columns": cols,
                }
            }
        },
        "LogicalTableMap": {
            "lt1": {
                "Alias": d["ds_name"],
                "Source": {"PhysicalTableId": "t1"}
            }
        },
    }
    return physical, cols


def field_well_dim(field_id, ds_id, col_name):
    return {
        "CategoricalDimensionField": {
            "FieldId": field_id,
            "Column": {"DataSetIdentifier": ds_id, "ColumnName": col_name},
        }
    }


def field_well_meas(field_id, ds_id, col_name, agg="SUM"):
    return {
        "NumericalMeasureField": {
            "FieldId": field_id,
            "Column": {"DataSetIdentifier": ds_id, "ColumnName": col_name},
            "AggregationFunction": {"SimpleNumericalAggregation": agg},
        }
    }


def field_well_dim_count(field_id, ds_id, col_name):
    return {
        "CategoricalMeasureField": {
            "FieldId": field_id,
            "Column": {"DataSetIdentifier": ds_id, "ColumnName": col_name},
            "AggregationFunction": "DISTINCT_COUNT",
        }
    }


def kpi_visual(d, idx, kpi):
    vid = f"kpi-{d['id']}-{idx}"
    ds_id = d["ds_id"]
    if kpi.get("agg") == "DISTINCT_COUNT":
        value_field = field_well_dim_count(f"v-{vid}", ds_id, kpi["field"])
    else:
        value_field = field_well_meas(f"v-{vid}", ds_id, kpi["field"], kpi.get("agg", "SUM"))

    visual = {
        "KPIVisual": {
            "VisualId": vid,
            "Title": {"Visibility": "VISIBLE", "FormatText": {"PlainText": kpi["label"]}},
            "Subtitle": {"Visibility": "HIDDEN"},
            "ChartConfiguration": {
                "FieldWells": {"Values": [value_field]},
            },
            "Actions": [],
        }
    }
    return visual


def bar_visual(d, idx, c):
    vid = f"bar-{d['id']}-{idx}"
    ds_id = d["ds_id"]
    cat = field_well_dim(f"x-{vid}", ds_id, c["x"][0])
    if len(c["y"]) == 3 and c["y"][2] == "DISTINCT_COUNT":
        val = field_well_dim_count(f"y-{vid}", ds_id, c["y"][0])
    else:
        agg = c["y"][2] if len(c["y"]) == 3 else "SUM"
        val = field_well_meas(f"y-{vid}", ds_id, c["y"][0], agg)

    field_wells = {
        "BarChartAggregatedFieldWells": {
            "Category": [cat],
            "Values": [val],
        }
    }
    if "color" in c:
        field_wells["BarChartAggregatedFieldWells"]["Colors"] = [
            field_well_dim(f"c-{vid}", ds_id, c["color"][0])
        ]

    return {
        "BarChartVisual": {
            "VisualId": vid,
            "Title": {"Visibility": "VISIBLE", "FormatText": {"PlainText": c["title"]}},
            "Subtitle": {"Visibility": "HIDDEN"},
            "ChartConfiguration": {
                "FieldWells": {"BarChartAggregatedFieldWells": field_wells["BarChartAggregatedFieldWells"]},
                "Orientation": "VERTICAL",
                "BarsArrangement": "CLUSTERED",
                "SortConfiguration": {
                    "CategorySort": [{"FieldSort": {"FieldId": f"y-{vid}", "Direction": "DESC"}}],
                    "CategoryItemsLimit": {"ItemsLimit": 20},
                },
                "Legend": {"Visibility": "VISIBLE" if "color" in c else "HIDDEN"},
                "DataLabels": {"Visibility": "HIDDEN"},
                "CategoryAxis": {
                    "AxisLineVisibility": "VISIBLE",
                    "GridLineVisibility": "HIDDEN",
                },
                "ValueAxis": {
                    "AxisLineVisibility": "HIDDEN",
                    "GridLineVisibility": "VISIBLE",
                },
            },
            "Actions": [],
        }
    }


def donut_visual(d, idx, c):
    vid = f"pie-{d['id']}-{idx}"
    ds_id = d["ds_id"]
    cat = field_well_dim(f"cat-{vid}", ds_id, c["category"][0])
    if len(c["value"]) == 3 and c["value"][2] == "DISTINCT_COUNT":
        val = field_well_dim_count(f"val-{vid}", ds_id, c["value"][0])
    else:
        agg = c["value"][2] if len(c["value"]) == 3 else "SUM"
        val = field_well_meas(f"val-{vid}", ds_id, c["value"][0], agg)

    return {
        "PieChartVisual": {
            "VisualId": vid,
            "Title": {"Visibility": "VISIBLE", "FormatText": {"PlainText": c["title"]}},
            "Subtitle": {"Visibility": "HIDDEN"},
            "ChartConfiguration": {
                "FieldWells": {
                    "PieChartAggregatedFieldWells": {
                        "Category": [cat],
                        "Values": [val],
                    }
                },
                "DonutOptions": {
                    "ArcOptions": {"ArcThickness": "MEDIUM"},
                    "DonutCenterOptions": {"LabelVisibility": "HIDDEN"},
                },
                "Legend": {"Visibility": "VISIBLE"},
                "DataLabels": {"Visibility": "VISIBLE", "LabelContent": "PERCENT"},
                "SortConfiguration": {
                    "CategoryItemsLimit": {"ItemsLimit": 10},
                    "CategorySort": [{"FieldSort": {"FieldId": f"val-{vid}", "Direction": "DESC"}}],
                },
            },
            "Actions": [],
        }
    }


def build_dashboard_definition(d, ds_arn):
    visuals = []
    layout_elements = []

    # 4 KPIs row 1: each col 8 wide of 36, height 4
    for i, kpi in enumerate(d["kpis"]):
        v = kpi_visual(d, i, kpi)
        vid = list(v.values())[0]["VisualId"]
        visuals.append(v)
        layout_elements.append({
            "ElementId": vid,
            "ElementType": "VISUAL",
            "ColumnIndex": i * 9,
            "ColumnSpan": 9,
            "RowIndex": 0,
            "RowSpan": 5,
        })

    # 2 charts row 2: each 18 wide, height 12
    for i, c in enumerate(d["charts"]):
        if c["type"] == "bar":
            v = bar_visual(d, i, c)
        else:
            v = donut_visual(d, i, c)
        vid = list(v.values())[0]["VisualId"]
        visuals.append(v)
        layout_elements.append({
            "ElementId": vid,
            "ElementType": "VISUAL",
            "ColumnIndex": i * 18,
            "ColumnSpan": 18,
            "RowIndex": 5,
            "RowSpan": 14,
        })

    sheet = {
        "SheetId": f"sheet-{d['id']}",
        "Name": d["name"],
        "Title": d["name"],
        "Description": d["name"],
        "Visuals": visuals,
        "Layouts": [{
            "Configuration": {
                "GridLayout": {
                    "Elements": layout_elements,
                    "CanvasSizeOptions": {
                        "ScreenCanvasSizeOptions": {
                            "ResizeOption": "FIXED",
                            "OptimizedViewPortWidth": "1600px",
                        }
                    },
                }
            }
        }],
        "ContentType": "INTERACTIVE",
    }

    return {
        "DataSetIdentifierDeclarations": [{
            "DataSetArn": ds_arn,
            "Identifier": d["ds_id"],
        }],
        "Sheets": [sheet],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", help="Single demo id (default: all)", default=None)
    parser.add_argument("--skip-dataset", action="store_true")
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--skip-topic", action="store_true")
    args = parser.parse_args()

    targets = [d for d in DEMOS if not args.demo or d["id"] == args.demo]
    summary = []

    for d in targets:
        print(f"\n=== {d['id']} ===")
        ds_arn = f"arn:aws:quicksight:{REGION}:{ACCOUNT}:dataset/{d['ds_id']}"

        if not args.skip_dataset:
            phys, cols = build_dataset(d)
            with open(f"/tmp/qs_build/ds-{d['id']}.json", "w") as f:
                json.dump(phys, f)
            r = subprocess.run([
                "aws", "quicksight", "describe-data-set", "--region", REGION,
                "--aws-account-id", ACCOUNT, "--data-set-id", d["ds_id"]
            ], capture_output=True, text=True)
            exists = (r.returncode == 0)
            op = "update-data-set" if exists else "create-data-set"
            cmd = [
                "aws", "quicksight", op, "--region", REGION,
                "--aws-account-id", ACCOUNT, "--data-set-id", d["ds_id"],
                "--name", d["ds_name"],
                "--physical-table-map", json.dumps(phys["PhysicalTableMap"]),
                "--logical-table-map", json.dumps(phys["LogicalTableMap"]),
                "--import-mode", "DIRECT_QUERY",
            ]
            if not exists:
                cmd += ["--permissions", json.dumps(DATASET_PERMS)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  DATASET ERROR: {r.stderr[:300]}")
                summary.append((d["id"], "dataset", "FAIL"))
                continue
            else:
                print(f"  dataset {d['ds_id']} {'updated' if exists else 'created'}")

        if not args.skip_dashboard:
            defn = build_dashboard_definition(d, ds_arn)
            with open(f"/tmp/qs_build/dash-{d['id']}.json", "w") as f:
                json.dump(defn, f)

            # check exist
            r = subprocess.run([
                "aws", "quicksight", "describe-dashboard", "--region", REGION,
                "--aws-account-id", ACCOUNT, "--dashboard-id", d["dashboard_id"]
            ], capture_output=True, text=True)
            exists = (r.returncode == 0)
            op = "update-dashboard" if exists else "create-dashboard"
            cmd = [
                "aws", "quicksight", op, "--region", REGION,
                "--aws-account-id", ACCOUNT, "--dashboard-id", d["dashboard_id"],
                "--name", d["dashboard_name"],
                "--definition", json.dumps(defn),
                "--theme-arn", THEME_ARN,
            ]
            if not exists:
                cmd += ["--permissions", json.dumps(DASH_PERMS)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  DASHBOARD ERROR: {r.stderr[:500]}")
                summary.append((d["id"], "dashboard", "FAIL"))
                continue
            print(f"  dashboard {d['dashboard_id']} {'updated' if exists else 'created'}")
            # publish
            r2 = subprocess.run([
                "aws", "quicksight", "update-dashboard-published-version", "--region", REGION,
                "--aws-account-id", ACCOUNT, "--dashboard-id", d["dashboard_id"],
                "--version-number", "1" if not exists else "2",
            ], capture_output=True, text=True)
            # may take multiple versions; loop
            for v in range(1, 8):
                r2 = subprocess.run([
                    "aws", "quicksight", "update-dashboard-published-version", "--region", REGION,
                    "--aws-account-id", ACCOUNT, "--dashboard-id", d["dashboard_id"],
                    "--version-number", str(v),
                ], capture_output=True, text=True)
                if r2.returncode == 0:
                    break

        summary.append((d["id"], "ok", "OK"))

    print("\n\n=== Summary ===")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
