"""Provision the AWS side of the demo and wire it to Snowflake.

Implemented path:
  Amazon Data Firehose (Direct PUT) -> S3 landing (engagement/) -> Snowpipe AUTO_INGEST (SQS) -> RAW.LIVE_ENGAGEMENT
  Amazon Bedrock (Claude) <- Snowflake external access UDF APP.BEDROCK_GENERATE

Dry-run by default. --apply creates or updates resources idempotently.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'snowflake'))

BEDROCK_PROFILE = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
BEDROCK_MODEL = 'anthropic.claude-sonnet-4-5-20250929-v1:0'


def ident(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
        raise ValueError(f'unsafe identifier {value!r}')
    return value


def names(prefix, account, region):
    p = prefix.lower()
    u = ident(p.upper().replace('-', '_'))
    return {
        'bucket': f'{p}-{account}-{region}',
        'snowflake_role': f'{p}-snowflake-s3',
        'firehose_role': f'{p}-firehose-s3',
        'firehose_stream': f'{p}-engagement',
        'bedrock_user': f'{p}-bedrock-invoke',
        'storage_int': f'{u}_S3_INT',
        'eai': f'{u}_BEDROCK_EAI',
    }


def ensure_role(iam, name, trust, policy_name, policy):
    try:
        iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust))
    except iam.exceptions.EntityAlreadyExistsException:
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(trust))
    iam.put_role_policy(RoleName=name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))
    return iam.get_role(RoleName=name)['Role']['Arn']


def firehose_request(n, bucket, role_arn):
    return {'DeliveryStreamName': n['firehose_stream'], 'DeliveryStreamType': 'DirectPut',
            'ExtendedS3DestinationConfiguration': {
                'RoleARN': role_arn, 'BucketARN': f'arn:aws:s3:::{bucket}', 'Prefix': 'engagement/',
                # Errors go outside engagement/ so Snowpipe never loads them.
                'ErrorOutputPrefix': 'firehose-errors/!{firehose:error-output-type}/',
                'BufferingHints': {'SizeInMBs': 1, 'IntervalInSeconds': 60}}}


def desc(cursor, sql):
    cursor.execute(sql)
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--connection', required=True, help='Snowflake connection name')
    ap.add_argument('--expect-account', help='Optional account locator guard; stops before writes on mismatch')
    ap.add_argument('--database', required=True)
    ap.add_argument('--account', required=True)
    ap.add_argument('--region', default='us-west-2')
    ap.add_argument('--prefix', default='sg-retail-customer-360')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    db = ident(args.database)
    n = names(args.prefix, args.account, args.region)
    print(json.dumps({'plan': n, 'database': db, 'apply': args.apply}, indent=2))
    if not args.apply:
        return

    import boto3
    from run_core import connect
    s3 = boto3.client('s3', region_name=args.region)
    iam = boto3.client('iam')
    firehose = boto3.client('firehose', region_name=args.region)
    bucket = n['bucket']
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': args.region})
    except (s3.exceptions.BucketAlreadyOwnedByYou,):
        pass
    s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
        'BlockPublicAcls': True, 'IgnorePublicAcls': True, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': True})
    s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
        'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]})

    read_policy = {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:GetObjectVersion'], 'Resource': f'arn:aws:s3:::{bucket}/engagement/*'},
        {'Effect': 'Allow', 'Action': ['s3:ListBucket', 's3:GetBucketLocation'], 'Resource': f'arn:aws:s3:::{bucket}',
         'Condition': {'StringLike': {'s3:prefix': ['engagement/*']}}}]}
    bootstrap = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow',
                 'Principal': {'AWS': f'arn:aws:iam::{args.account}:root'}, 'Action': 'sts:AssumeRole'}]}
    try:
        trust = iam.get_role(RoleName=n['snowflake_role'])['Role']['AssumeRolePolicyDocument']
    except iam.exceptions.NoSuchEntityException:
        trust = bootstrap
    sf_role_arn = ensure_role(iam, n['snowflake_role'], trust, 's3-read-engagement', read_policy)

    con = connect(args.connection)
    cur = con.cursor()
    cur.execute('SELECT CURRENT_ACCOUNT()')
    if args.expect_account and cur.fetchone()[0] != args.expect_account.upper():
        raise RuntimeError('Snowflake identity mismatch')
    cur.execute(f"""CREATE STORAGE INTEGRATION IF NOT EXISTS {n['storage_int']} TYPE = EXTERNAL_STAGE
        STORAGE_PROVIDER = 'S3' ENABLED = TRUE STORAGE_AWS_ROLE_ARN = '{sf_role_arn}'
        STORAGE_ALLOWED_LOCATIONS = ('s3://{bucket}/engagement/')""")
    props = {r['property']: r['property_value'] for r in desc(cur, f"DESC STORAGE INTEGRATION {n['storage_int']}")}
    trust = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow',
             'Principal': {'AWS': props['STORAGE_AWS_IAM_USER_ARN']}, 'Action': 'sts:AssumeRole',
             'Condition': {'StringEquals': {'sts:ExternalId': props['STORAGE_AWS_EXTERNAL_ID']}}}]}
    iam.update_assume_role_policy(RoleName=n['snowflake_role'], PolicyDocument=json.dumps(trust))
    time.sleep(10)

    cur.execute(f'USE DATABASE {db}')
    for stmt in [
        'CREATE SCHEMA IF NOT EXISTS RAW', 'CREATE SCHEMA IF NOT EXISTS APP',
        f"CREATE STAGE IF NOT EXISTS RAW.EVENT_LANDING STORAGE_INTEGRATION = {n['storage_int']} "
        f"URL = 's3://{bucket}/engagement/' FILE_FORMAT = (TYPE = JSON)",
        """CREATE TABLE IF NOT EXISTS RAW.LIVE_ENGAGEMENT (
            COHORT_ID VARCHAR, EVENT_TS TIMESTAMP_NTZ, AMOUNT_SGD FLOAT, RESPONSE_MINUTES FLOAT,
            STATUS VARCHAR, SENT_TS TIMESTAMP_NTZ, SOURCE_FILE VARCHAR,
            LOADED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP())""",
        """CREATE PIPE IF NOT EXISTS RAW.LIVE_ENGAGEMENT_PIPE AUTO_INGEST = TRUE AS
            COPY INTO RAW.LIVE_ENGAGEMENT (COHORT_ID, EVENT_TS, AMOUNT_SGD, RESPONSE_MINUTES, STATUS, SENT_TS, SOURCE_FILE)
            FROM (SELECT $1:cohort_id::VARCHAR, $1:event_ts::TIMESTAMP_NTZ, $1:amount_sgd::FLOAT,
                         $1:response_minutes::FLOAT, $1:status::VARCHAR,
                         TO_TIMESTAMP_NTZ($1:sent_ms::NUMBER, 3), METADATA$FILENAME
                  FROM @RAW.EVENT_LANDING)""",
    ]:
        cur.execute(stmt)
    pipe = desc(cur, "SHOW PIPES LIKE 'LIVE_ENGAGEMENT_PIPE' IN SCHEMA RAW")[0]
    s3.put_bucket_notification_configuration(Bucket=bucket, NotificationConfiguration={
        'QueueConfigurations': [{'QueueArn': pipe['notification_channel'], 'Events': ['s3:ObjectCreated:*'],
                                 'Filter': {'Key': {'FilterRules': [{'Name': 'prefix', 'Value': 'engagement/'}]}}}]})

    fh_trust = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow',
                'Principal': {'Service': 'firehose.amazonaws.com'}, 'Action': 'sts:AssumeRole',
                'Condition': {'StringEquals': {'sts:ExternalId': args.account}}}]}
    fh_role_arn = ensure_role(iam, n['firehose_role'], fh_trust, 's3-put-engagement', {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['s3:PutObject', 's3:AbortMultipartUpload'], 'Resource': [f'arn:aws:s3:::{bucket}/engagement/*', f'arn:aws:s3:::{bucket}/firehose-errors/*']},
        {'Effect': 'Allow', 'Action': ['s3:GetBucketLocation', 's3:ListBucket', 's3:ListBucketMultipartUploads'],
         'Resource': f'arn:aws:s3:::{bucket}'}]})
    time.sleep(10)
    try:
        firehose.create_delivery_stream(**firehose_request(n, bucket, fh_role_arn))
    except firehose.exceptions.ResourceInUseException:
        pass

    # Bedrock: least-privilege IAM user whose key lives only in a Snowflake secret.
    try:
        iam.create_user(UserName=n['bedrock_user'])
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    iam.put_user_policy(UserName=n['bedrock_user'], PolicyName='invoke-claude', PolicyDocument=json.dumps({
        'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Action': 'bedrock:InvokeModel', 'Resource': [
            f'arn:aws:bedrock:{args.region}:{args.account}:inference-profile/{BEDROCK_PROFILE}',
            f'arn:aws:bedrock:*::foundation-model/{BEDROCK_MODEL}']}]}))
    cur.execute("SHOW SECRETS LIKE 'BEDROCK_CREDENTIALS' IN SCHEMA APP")
    if not cur.fetchall():
        for old in iam.list_access_keys(UserName=n['bedrock_user'])['AccessKeyMetadata']:
            iam.delete_access_key(UserName=n['bedrock_user'], AccessKeyId=old['AccessKeyId'])
        key = iam.create_access_key(UserName=n['bedrock_user'])['AccessKey']
        cur.execute('CREATE SECRET APP.BEDROCK_CREDENTIALS TYPE = PASSWORD USERNAME = %s PASSWORD = %s',
                    (key['AccessKeyId'], key['SecretAccessKey']))
        time.sleep(10)
    for stmt in [
        f"CREATE NETWORK RULE IF NOT EXISTS APP.BEDROCK_EGRESS MODE = EGRESS TYPE = HOST_PORT "
        f"VALUE_LIST = ('bedrock-runtime.{args.region}.amazonaws.com:443')",
        f"CREATE EXTERNAL ACCESS INTEGRATION IF NOT EXISTS {n['eai']} ALLOWED_NETWORK_RULES = ({db}.APP.BEDROCK_EGRESS) "
        f"ALLOWED_AUTHENTICATION_SECRETS = ({db}.APP.BEDROCK_CREDENTIALS) ENABLED = TRUE",
        f"""CREATE OR REPLACE FUNCTION APP.BEDROCK_GENERATE(PROMPT VARCHAR) RETURNS VARCHAR LANGUAGE PYTHON
            RUNTIME_VERSION = '3.11' PACKAGES = ('boto3') HANDLER = 'run'
            EXTERNAL_ACCESS_INTEGRATIONS = ({n['eai']}) SECRETS = ('cred' = APP.BEDROCK_CREDENTIALS)
            AS $$
import json, boto3, _snowflake
def run(prompt):
    c = _snowflake.get_username_password('cred')
    client = boto3.client('bedrock-runtime', region_name='{args.region}',
                          aws_access_key_id=c.username, aws_secret_access_key=c.password)
    body = json.dumps({{'anthropic_version': 'bedrock-2023-05-31', 'max_tokens': 600,
                       'messages': [{{'role': 'user', 'content': prompt}}]}})
    out = client.invoke_model(modelId='{BEDROCK_PROFILE}', body=body,
                              contentType='application/json', accept='application/json')
    return json.loads(out['body'].read())['content'][0]['text']
$$""",
    ]:
        cur.execute(stmt)
    print(json.dumps({'bucket': bucket, 'pipe_sqs': pipe['notification_channel'], 'firehose_stream': n['firehose_stream'],
                      'storage_integration': n['storage_int'], 'eai': n['eai']}, indent=2))


if __name__ == '__main__':
    main()
