"""Run 05_ml.sql and/or 06_intelligence.sql against an isolated demo database.

Only checked identifiers and an email address are substituted into the SQL.
Usage: python snowflake/run_intelligence.py --database SINGAPORE_RETAIL_CUSTOMER_360_AWS --alert-email you@example.com \
       [--platform snowflake|aws] [--files 06_intelligence.sql]
--platform snowflake runs 08_native_engagement.sql first (no AWS needed); aws expects
aws/setup_aws.py to have created RAW.LIVE_ENGAGEMENT and its Snowpipe.
"""
import argparse
import io
import re
import sys
from pathlib import Path

from run_core import checked_identifier, connect, validate_target

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--connection', required=True, help='Snowflake connection name')
    ap.add_argument('--expect-account', help='Optional account locator guard; stops before writes on mismatch')
    ap.add_argument('--database', required=True)
    ap.add_argument('--warehouse', required=True)
    ap.add_argument('--alert-email', required=True)
    ap.add_argument('--platform', choices=['snowflake', 'aws'], default='aws')
    ap.add_argument('--files', nargs='+')
    ap.add_argument('--compute-pool', help='Existing SPCS compute pool; required for 07_deploy_app.sql')
    args = ap.parse_args()
    if not args.files:
        args.files = (['08_native_engagement.sql'] if args.platform == 'snowflake' else []) + ['05_ml.sql', '06_intelligence.sql']
    validate_target(args.database, args.warehouse)
    if '07_deploy_app.sql' in args.files:
        if not args.compute_pool:
            raise ValueError('--compute-pool is required for 07_deploy_app.sql')
        checked_identifier(args.compute_pool)
    if not re.fullmatch(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', args.alert_email):
        raise ValueError('invalid email')
    from snowflake.connector.util_text import split_statements
    con = connect(args.connection)
    cur = con.cursor()
    cur.execute('SELECT CURRENT_ACCOUNT()')
    if args.expect_account and cur.fetchone()[0] != args.expect_account.upper():
        raise RuntimeError('Snowflake identity mismatch')
    cur.execute('SET DEMO_DB = %s', (args.database,))
    cur.execute('SET DEMO_WH = %s', (args.warehouse,))
    cur.execute(f'USE DATABASE {args.database}')
    cur.execute(f'USE WAREHOUSE {args.warehouse}')
    try:
        for name in args.files:
            sql = (HERE / name).read_text()
            sql = (sql.replace('__DEMO_DB__', args.database).replace('__DEMO_WH__', args.warehouse)
                      .replace('__ALERT_EMAIL__', args.alert_email)
                   .replace('__DEMO_PLATFORM__', args.platform)
                   .replace('__COMPUTE_POOL__', args.compute_pool or ''))
            for statement, _ in split_statements(io.StringIO(sql)):
                if statement.strip():
                    cur.execute(statement)
                    first = [l for l in statement.strip().splitlines() if not l.startswith('--')]
                    print('ok', name, cur.sfqid, (first[0] if first else '')[:80])
    finally:
        try:
            cur.execute(f'ALTER WAREHOUSE {args.warehouse} SUSPEND')
        except Exception:
            pass  # already suspended


if __name__ == '__main__':
    sys.exit(main())
