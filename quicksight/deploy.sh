#!/usr/bin/env bash
set -euo pipefail

REGION="us-west-2"
ACCT="__AWS_ACCOUNT_ID__"
DS_ID="fsi-snowflake-ds"
DS_ARN="arn:aws:quicksight:${REGION}:${ACCT}:datasource/${DS_ID}"
QS_USER_ARN="arn:aws:quicksight:us-west-2:__AWS_ACCOUNT_ID__:user/default/__AWS_ACCOUNT_ID__"

fail() { echo "FAILED: $1"; exit 1; }
ok()   { echo "  OK: $1"; }

echo "=== Customer 360 & Loyalty QuickSight Deployment ==="

echo "Creating dataset: c360-customer-profile..."
aws quicksight create-data-set \
  --aws-account-id "$ACCT" --region "$REGION" \
  --data-set-id "c360-customer-profile" \
  --name "Customer 360 - Customer Profile" \
  --import-mode DIRECT_QUERY \
  --physical-table-map '{
    "profile": {
      "CustomSql": {
        "DataSourceArn": "'"${DS_ARN}"'",
        "Name": "CustomerProfile",
        "SqlQuery": "SELECT CUSTOMER_ID, FIRST_NAME, LAST_NAME, TIER, CITY, COUNTRY, AGE_GROUP, PREFERRED_CHANNEL, LIFETIME_SPEND, TXN_COUNT, AVG_BASKET, DAYS_SINCE_LAST_TXN, LOYALTY_POINTS, AVG_FEEDBACK_RATING, OPEN_TICKETS, CUSTOMER_SEGMENT FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE",
        "Columns": [
          {"Name": "CUSTOMER_ID", "Type": "STRING"},
          {"Name": "FIRST_NAME", "Type": "STRING"},
          {"Name": "LAST_NAME", "Type": "STRING"},
          {"Name": "TIER", "Type": "STRING"},
          {"Name": "CITY", "Type": "STRING"},
          {"Name": "COUNTRY", "Type": "STRING"},
          {"Name": "AGE_GROUP", "Type": "STRING"},
          {"Name": "PREFERRED_CHANNEL", "Type": "STRING"},
          {"Name": "LIFETIME_SPEND", "Type": "DECIMAL"},
          {"Name": "TXN_COUNT", "Type": "INTEGER"},
          {"Name": "AVG_BASKET", "Type": "DECIMAL"},
          {"Name": "DAYS_SINCE_LAST_TXN", "Type": "INTEGER"},
          {"Name": "LOYALTY_POINTS", "Type": "INTEGER"},
          {"Name": "AVG_FEEDBACK_RATING", "Type": "DECIMAL"},
          {"Name": "OPEN_TICKETS", "Type": "INTEGER"},
          {"Name": "CUSTOMER_SEGMENT", "Type": "STRING"}
        ]
      }
    }
  }' \
  --permissions '[{"Principal":"'"${QS_USER_ARN}"'","Actions":["quicksight:DescribeDataSet","quicksight:DescribeDataSetPermissions","quicksight:PassDataSet","quicksight:DescribeIngestion","quicksight:ListIngestions","quicksight:UpdateDataSet","quicksight:DeleteDataSet","quicksight:CreateIngestion","quicksight:CancelIngestion","quicksight:UpdateDataSetPermissions"]}]' \
  2>&1 && ok "Dataset: c360-customer-profile" || fail "Dataset creation"

echo "Creating dataset: c360-campaign-performance..."
aws quicksight create-data-set \
  --aws-account-id "$ACCT" --region "$REGION" \
  --data-set-id "c360-campaign-performance" \
  --name "Customer 360 - Campaign Performance" \
  --import-mode DIRECT_QUERY \
  --physical-table-map '{
    "campaigns": {
      "CustomSql": {
        "DataSourceArn": "'"${DS_ARN}"'",
        "Name": "CampaignPerformance",
        "SqlQuery": "SELECT CAMPAIGN_NAME, CHANNEL, TARGET_SEGMENT, BUDGET, TOTAL_RESPONSES, OPENS, CLICKS, CONVERSIONS, UNSUBSCRIBES, OPEN_RATE, CLICK_RATE, CONVERSION_RATE FROM RETAIL_CUSTOMER_360.CURATED.CAMPAIGN_PERFORMANCE",
        "Columns": [
          {"Name": "CAMPAIGN_NAME", "Type": "STRING"},
          {"Name": "CHANNEL", "Type": "STRING"},
          {"Name": "TARGET_SEGMENT", "Type": "STRING"},
          {"Name": "BUDGET", "Type": "DECIMAL"},
          {"Name": "TOTAL_RESPONSES", "Type": "INTEGER"},
          {"Name": "OPENS", "Type": "INTEGER"},
          {"Name": "CLICKS", "Type": "INTEGER"},
          {"Name": "CONVERSIONS", "Type": "INTEGER"},
          {"Name": "UNSUBSCRIBES", "Type": "INTEGER"},
          {"Name": "OPEN_RATE", "Type": "DECIMAL"},
          {"Name": "CLICK_RATE", "Type": "DECIMAL"},
          {"Name": "CONVERSION_RATE", "Type": "DECIMAL"}
        ]
      }
    }
  }' \
  --permissions '[{"Principal":"'"${QS_USER_ARN}"'","Actions":["quicksight:DescribeDataSet","quicksight:DescribeDataSetPermissions","quicksight:PassDataSet","quicksight:DescribeIngestion","quicksight:ListIngestions","quicksight:UpdateDataSet","quicksight:DeleteDataSet","quicksight:CreateIngestion","quicksight:CancelIngestion","quicksight:UpdateDataSetPermissions"]}]' \
  2>&1 && ok "Dataset: c360-campaign-performance" || fail "Dataset creation"

echo "Creating Q topic: customer-360-q-topic..."
Q_TOPIC_DEF=$(mktemp)
cat > "$Q_TOPIC_DEF" <<EOJSON
{
  "AwsAccountId": "${ACCT}",
  "TopicId": "customer-360-q-topic",
  "Topic": {
    "Name": "Customer 360 & Loyalty",
    "Description": "Customer profiles, segmentation, churn risk, and campaign performance for APJ retail",
    "DataSets": [{
      "DatasetArn": "arn:aws:quicksight:${REGION}:${ACCT}:dataset/c360-customer-profile",
      "DatasetName": "Customer Profile",
      "Columns": [
        {"ColumnName": "TIER", "ColumnFriendlyName": "Tier", "ColumnSynonyms": ["membership","level","grade"], "IsIncludedInTopic": true},
        {"ColumnName": "CUSTOMER_SEGMENT", "ColumnFriendlyName": "Segment", "ColumnSynonyms": ["group","cohort","type"], "IsIncludedInTopic": true},
        {"ColumnName": "COUNTRY", "ColumnFriendlyName": "Country", "ColumnSynonyms": ["market","region"], "IsIncludedInTopic": true},
        {"ColumnName": "LIFETIME_SPEND", "ColumnFriendlyName": "CLV", "ColumnSynonyms": ["lifetime value","total spend","revenue"], "IsIncludedInTopic": true},
        {"ColumnName": "LOYALTY_POINTS", "ColumnFriendlyName": "Points", "ColumnSynonyms": ["rewards","balance"], "IsIncludedInTopic": true},
        {"ColumnName": "DAYS_SINCE_LAST_TXN", "ColumnFriendlyName": "Recency", "ColumnSynonyms": ["days since","last purchase","inactive days"], "IsIncludedInTopic": true}
      ]
    }]
  }
}
EOJSON

aws quicksight create-topic --cli-input-json "file://${Q_TOPIC_DEF}" --region "$REGION" 2>&1 \
  && ok "Q Topic: customer-360-q-topic" || echo "  WARN: Q Topic may already exist"
rm -f "$Q_TOPIC_DEF"

echo ""
echo "=== Customer 360 QuickSight Done ==="
echo "Try Q: 'How many Gold customers have churned?' or 'What is the average CLV by segment?'"
