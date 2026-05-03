USE ROLE ACCOUNTADMIN;
USE DATABASE RETAIL_CUSTOMER_360;
USE WAREHOUSE WH_CUSTOMER_360;

CREATE NETWORK RULE IF NOT EXISTS RETAIL_CUSTOMER_360.AI.BEDROCK_NETWORK_RULE
    TYPE = HOST_PORT MODE = EGRESS VALUE_LIST = ('bedrock-runtime.us-west-2.amazonaws.com:443');

CREATE SECRET IF NOT EXISTS RETAIL_CUSTOMER_360.AI.BEDROCK_SECRET
    TYPE = GENERIC_STRING SECRET_STRING = '{}';

CREATE EXTERNAL ACCESS INTEGRATION IF NOT EXISTS RETAIL_C360_BEDROCK_EAI
    ALLOWED_NETWORK_RULES = (RETAIL_CUSTOMER_360.AI.BEDROCK_NETWORK_RULE)
    ALLOWED_AUTHENTICATION_SECRETS = (RETAIL_CUSTOMER_360.AI.BEDROCK_SECRET)
    ENABLED = TRUE
    COMMENT = 'External Access Integration for Amazon Bedrock (Customer 360 - personalized NBA)';

CREATE NETWORK RULE IF NOT EXISTS RETAIL_CUSTOMER_360.AI.SES_NETWORK_RULE
    TYPE = HOST_PORT MODE = EGRESS VALUE_LIST = ('email.us-west-2.amazonaws.com:443');

CREATE SECRET IF NOT EXISTS RETAIL_CUSTOMER_360.AI.SES_SECRET
    TYPE = GENERIC_STRING SECRET_STRING = '{}';

CREATE EXTERNAL ACCESS INTEGRATION IF NOT EXISTS RETAIL_C360_SES_EAI
    ALLOWED_NETWORK_RULES = (RETAIL_CUSTOMER_360.AI.SES_NETWORK_RULE)
    ALLOWED_AUTHENTICATION_SECRETS = (RETAIL_CUSTOMER_360.AI.SES_SECRET)
    ENABLED = TRUE
    COMMENT = 'External Access Integration for Amazon SES (Customer 360 - churn re-engagement emails)';

-- After populating secrets with real AWS credentials:
--   ALTER SECRET RETAIL_CUSTOMER_360.AI.BEDROCK_SECRET
--     SET SECRET_STRING = '{"aws_access_key_id":"AKIA...","aws_secret_access_key":"..."}';
--   ALTER SECRET RETAIL_CUSTOMER_360.AI.SES_SECRET
--     SET SECRET_STRING = '{"aws_access_key_id":"AKIA...","aws_secret_access_key":"..."}';

CREATE OR REPLACE FUNCTION RETAIL_CUSTOMER_360.AI.BEDROCK_GENERATE_NBA(prompt STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('boto3', 'snowflake-snowpark-python')
HANDLER = 'generate_nba'
EXTERNAL_ACCESS_INTEGRATIONS = (RETAIL_C360_BEDROCK_EAI)
SECRETS = ('aws_creds' = RETAIL_CUSTOMER_360.AI.BEDROCK_SECRET)
AS $$
import json, boto3, _snowflake

def generate_nba(prompt):
    creds = json.loads(_snowflake.get_generic_secret_string('aws_creds'))
    client = boto3.client('bedrock-runtime', region_name='us-west-2',
        aws_access_key_id=creds['aws_access_key_id'],
        aws_secret_access_key=creds['aws_secret_access_key'])
    response = client.invoke_model(
        modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        contentType='application/json', accept='application/json',
        body=json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]}))
    result = json.loads(response['body'].read())
    return result['content'][0]['text']
$$;

CREATE OR REPLACE FUNCTION RETAIL_CUSTOMER_360.AI.SES_SEND_EMAIL(
    recipient STRING, subject STRING, body_html STRING, sender STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('boto3', 'snowflake-snowpark-python')
HANDLER = 'send_email'
EXTERNAL_ACCESS_INTEGRATIONS = (RETAIL_C360_SES_EAI)
SECRETS = ('aws_creds' = RETAIL_CUSTOMER_360.AI.SES_SECRET)
AS $$
import json, boto3, _snowflake

def send_email(recipient, subject, body_html, sender):
    creds = json.loads(_snowflake.get_generic_secret_string('aws_creds'))
    client = boto3.client('ses', region_name='us-west-2',
        aws_access_key_id=creds['aws_access_key_id'],
        aws_secret_access_key=creds['aws_secret_access_key'])
    try:
        response = client.send_email(
            Source=sender, Destination={'ToAddresses': [recipient]},
            Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': body_html}}})
        return json.dumps({"status": "sent", "message_id": response['MessageId']})
    except client.exceptions.MessageRejected as e:
        return json.dumps({"status": "sandbox_restricted", "error": str(e), "note": "SES sandbox mode - verify sender/recipient emails for production"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
$$;
