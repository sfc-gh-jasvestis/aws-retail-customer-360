"""Render docs/architecture-{aws,snowflake}.html (and app copies) for both build options.

Grid: 12 cols x 8 rows on a 1400x700 viewBox; cx = 95 + (col-1)*110, cy = 70 + (row-1)*80.
Brand CSS/JS/logo are taken from the architecture-diagram skill presets when available.
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PRESETS = os.environ.get(
    'DIAGRAM_PRESETS',
    os.path.expanduser('~/Downloads/sizing-agent-skills/skills/architecture-diagram/DIAGRAM_PRESETS.md'),
)
HW, HH = 46, 26  # node half-width / half-height


def cx(col):
    return 95 + (col - 1) * 110


def cy(row):
    return 70 + (row - 1) * 80


# id: (label, sublabel, col, row, body class, tooltip)
NODES = {
    'SIM': ('Engagement sim', 'publish_engagement.py', 1, 2, 'source',
            'Sends synthetic engagement events (cohort, basket amount in SGD, service response minutes, status) to Amazon Data Firehose with PutRecordBatch.'),
    'FH': ('Data Firehose', 'Direct PUT stream', 2, 2, 'ingestion',
            'Firehose stream sg-retail-customer-360-engagement (Direct PUT); buffers up to 60 s or 1 MB, then writes newline-delimited JSON to S3 under engagement/.'),
    'S3': ('Amazon S3', 'landing bucket', 3, 2, 'ingestion',
           'JSON objects land under the engagement/ prefix; read through storage integration SG_RETAIL_CUSTOMER_360_S3_INT. Firehose errors go to firehose-errors/.'),
    'SQS': ('Amazon SQS', 'S3 event notification', 4, 2, 'ingestion',
            'S3 object-created events go to the Snowpipe-managed SQS queue (AUTO_INGEST).'),
    'PIPE': ('Snowpipe', 'AUTO_INGEST', 5, 2, 'snowflake',
             'Serverless COPY from the external stage into RAW.LIVE_ENGAGEMENT.'),
    'LIVE': ('Live engagement', 'RAW schema', 6, 2, 'snowflake',
             'RAW.LIVE_ENGAGEMENT: landed engagement events. Feeds the Live Engagement tab, the service-issue alert and the QuickSight events dataset.'),
    'ALERT': ('Alert + email', 'on ISSUE', 7, 1, 'governance',
              'APP.LIVE_ENGAGEMENT_ALERT fires on ISSUE events, writes APP.ALERT_LOG and sends email through SYSTEM$SEND_EMAIL (SG_RETAIL_CUSTOMER_360_EMAIL_INT). Suspended between demos.'),
    'SEED': ('Synthetic seed', 'deterministic SQL', 5, 4, 'source',
             'Synthetic loyalty cohorts in 5 Singapore planning areas, daily aggregate cohort observations and profile field completeness created by 02_raw_tables.sql. No individual customer records.'),
    'RAW': ('RAW tables', 'cohorts · days · profiles', 6, 4, 'snowflake',
            'Source-of-truth synthetic tables in the RAW schema.'),
    'DT': ('Curated DTs', 'dynamic tables', 7, 4, 'snowflake',
           'Curated dynamic tables compute numerator/denominator metrics (issue-free purchase rate, issue churn rate, CRM touch compliance, profile completeness). Suspended after initialization.'),
    'ML': ('Snowflake ML', '3 models', 8, 4, 'compute',
           'CLASSIFICATION churn risk to ML.CHURN_RISK_SCORES (time-based holdout), 14-day service-issue FORECAST, ANOMALY_DETECTION to ML.RETURN_RATE_ANOMALIES.'),
    'APP': ('Next.js app', 'SPCS service', 10, 4, 'app',
            'APP.SG_RETAIL_CUSTOMER_360_APP. Routes /api/data, /api/agent, /api/ask.'),
    'UDF': ('Bedrock UDF', 'external access', 11, 4, 'compute',
            'Python UDF APP.BEDROCK_GENERATE calls Bedrock with boto3 through external access integration SG_RETAIL_CUSTOMER_360_BEDROCK_EAI. Used by /api/ask for the action memo.'),
    'BED': ('Amazon Bedrock', 'Claude Sonnet 4.5', 12, 4, 'consumer',
            'Inference profile us.anthropic.claude-sonnet-4-5-20250929-v1:0 in us-west-2.'),
    'QS': ('QuickSight + Q', 'dashboard · Q topic', 12, 2, 'consumer',
           'DIRECT_QUERY dashboard sg-retail-customer-360-dashboard and Q topic sg-retail-customer-360-topic, through a PAT-only, role-restricted Snowflake service user.'),
    'TASK': ('Task graph', 'refresh → rescore', 7, 6, 'snowflake',
             'APP.TASK_REFRESH_CURATED refreshes the curated DTs, then TASK_RESCORE_RISK rescores churn risk. Run on demand.'),
    'SEARCH': ('Cortex Search', 'service-issue SOPs', 8, 6, 'compute',
               'SEARCH.ISSUE_SOP_SEARCH over the synthetic service-issue handling SOPs.'),
    'AGENT': ('Cortex Agent', 'analyst + search', 9, 6, 'compute',
              'APP.CUSTOMER360_AGENT: Cortex Analyst over semantic view APP.CUSTOMER360_ANALYTICS plus Cortex Search for SOP citations.'),
}

# (class, d, marker or None, label, label x, label y)
CONNECTORS = [
    ('connector connector-animated', 'M141,150 L159,150', 'blue', None, 0, 0),
    ('connector connector-animated', 'M251,150 L269,150', 'blue', None, 0, 0),
    ('connector connector-animated', 'M361,150 L379,150', 'blue', None, 0, 0),
    ('connector connector-animated', 'M471,150 L489,150', 'blue', None, 0, 0),
    ('connector connector-animated', 'M581,150 L599,150', 'blue', None, 0, 0),
    ('connector connector-secondary', 'M645,124 L645,78 Q645,70 653,70 L709,70', 'blue', None, 0, 0),
    ('connector connector-animated', 'M691,150 L1259,150', 'blue', 'DIRECT_QUERY', 1180, 140),
    ('connector connector-primary', 'M1085,150 L1085,284', 'blue', 'Live Engagement', 1112, 217),
    ('connector connector-primary', 'M755,284 L755,158 Q755,150 763,150', None, 'curated', 780, 217),
    ('connector connector-primary', 'M895,284 L895,158 Q895,150 903,150', None, 'risk', 912, 217),
    ('connector connector-primary', 'M581,310 L599,310', 'blue', None, 0, 0),
    ('connector connector-primary', 'M691,310 L709,310', 'blue', None, 0, 0),
    ('connector connector-primary', 'M801,310 L819,310', 'blue', None, 0, 0),
    ('connector connector-primary', 'M911,310 L1039,310', 'blue', '/api/data', 975, 300),
    ('connector connector-highlight', 'M1131,310 L1149,310', 'orange', None, 0, 0),
    ('connector connector-highlight', 'M1241,310 L1259,310', 'orange', None, 0, 0),
    ('connector connector-subtle', 'M755,444 L755,336', None, 'refresh', 735, 390),
    ('connector connector-primary', 'M865,336 L865,382 Q865,390 873,390 L967,390 Q975,390 975,398 L975,444',
     'blue', 'semantic view', 922, 380),
    ('connector connector-primary', 'M911,470 L929,470', 'blue', None, 0, 0),
    ('connector connector-primary', 'M1021,470 L1077,470 Q1085,470 1085,462 L1085,336', 'blue', '/api/agent', 1050, 460),
]

ZONES = [
    ('zone-bg-ingestion', 40, 30, 440, 160, 'AWS INGESTION', 'your AWS account · us-west-2'),
    ('zone-bg-snowflake', 482, 30, 768, 640, 'SNOWFLAKE', ''),
    ('zone-bg-consumers', 1252, 30, 108, 640, 'AWS AI + BI', ''),
]

# Snowflake-only build: no AWS ingestion zone, no QuickSight, memo through Cortex.
SF_ONLY_DROP = {'SIM', 'FH', 'S3', 'SQS', 'PIPE', 'UDF', 'BED', 'QS'}
SF_ONLY_NODES = {
    'NATIVE': ('Engagement sim', 'stored procedure', 5, 2, 'compute',
               'CALL APP.SIMULATE_ENGAGEMENT(n) inserts simulated engagement events (same ranges and ~10% ISSUE rate as the AWS publisher) directly into RAW.LIVE_ENGAGEMENT. Optional task APP.TASK_SIMULATE_ENGAGEMENT runs it every minute.'),
    'CORTEX': ('AI_COMPLETE', 'claude-sonnet-4-5', 11, 4, 'compute',
               'Snowflake Cortex AI_COMPLETE writes the action memo for /api/ask from KPI, cohort, issue-type and risk rows only.'),
}
SF_ONLY_KEEP = {5, 10, 11, 12, 13, 16, 17, 18, 19}
SF_ONLY_CONNECTORS = [
    ('connector connector-animated', 'M581,150 L599,150', 'blue', None, 0, 0),
    ('connector connector-animated', 'M691,150 L1077,150 Q1085,150 1085,158 L1085,284', 'blue', 'Live Engagement', 1112, 217),
    ('connector connector-highlight', 'M1131,310 L1149,310', 'orange', None, 0, 0),
]
SF_ONLY_ZONES = [
    ('zone-bg-snowflake', 40, 30, 1320, 640, 'SNOWFLAKE ONLY', 'no AWS account required'),
]

VARIANTS = {
    'aws': dict(nodes=NODES, connectors=CONNECTORS, zones=ZONES,
                subtitle='AWS Firehose + Bedrock + QuickSight on Snowflake', notes=None),
    'snowflake': dict(
        nodes={**{k: v for k, v in NODES.items() if k not in SF_ONLY_DROP}, **SF_ONLY_NODES},
        connectors=[c for i, c in enumerate(CONNECTORS) if i in SF_ONLY_KEEP] + SF_ONLY_CONNECTORS,
        zones=SF_ONLY_ZONES, subtitle='Snowflake-only build: ML, Cortex AI and SPCS',
        notes=('SINGAPORE_RETAIL_CUSTOMER_360_SNOWFLAKE · synthetic demo data',
               'Every flow shown is built by the scripts in this repository.')),
}

NOTES = ('SINGAPORE_RETAIL_CUSTOMER_360_AWS · synthetic demo data',
         'Every flow shown is built by the scripts in this repository.')


def fence(md, heading, lang):
    sec = md.split(heading, 1)[1]
    return re.search(r'```' + lang + r'\n(.*?)```', sec, re.S).group(1)


def render(variant):
    v = VARIANTS[variant]
    with open(PRESETS, encoding='utf-8') as f:
        md = f.read()
    css = fence(md, '## Complete Mandatory CSS', 'css')
    js = fence(md, '## Complete Required JavaScript', 'javascript')
    logo = fence(md, '## Snowflake Bug SVG (Header)', 'html')
    # Embedded in the app iframe: keep the page scroll-free and transparent to wheel events outside the SVG.
    css += '\n.zone-note { font-family: Arial, Helvetica, sans-serif; font-size: 10px; fill: var(--sf-gray); }\n'

    out = []
    for cls, x, y, w, h, title, sub in v['zones']:
        out.append(f'<rect class="zone-bg {cls}" x="{x}" y="{y}" width="{w}" height="{h}" />')
        out.append(f'<text class="zone-title" x="{x + 12}" y="{y + 18}">{title}</text>')
        if sub:
            out.append(f'<text class="zone-subtitle" x="{x + 12}" y="{y + 32}">{html.escape(sub)}</text>')
    for i, note in enumerate(v['notes'] or NOTES):
        out.append(f'<text class="zone-note" x="500" y="{630 + 16 * i}">{html.escape(note)}</text>')
    for cls, d, marker, label, lx, ly in v['connectors']:
        m = f' marker-end="url(#arrowhead-{marker})"' if marker else ''
        out.append(f'<path class="{cls}" d="{d}"{m} />')
        if label:
            w = len(label) * 4.6 + 8
            out.append(f'<rect class="connector-label-bg" x="{lx - w / 2:.0f}" y="{ly - 6}" width="{w:.0f}" height="12" />')
            out.append(f'<text class="connector-label" x="{lx}" y="{ly}">{html.escape(label)}</text>')
    for label, sub, col, row, body, tip in v['nodes'].values():
        out.append(
            f'<g class="node" transform="translate({cx(col)}, {cy(row)})" '
            f'data-tooltip-title="{html.escape(label)}" data-tooltip="{html.escape(tip)}">'
            f'<rect class="node-body node-body-{body}" x="{-HW}" y="{-HH}" width="{2 * HW}" height="{2 * HH}" '
            f'rx="8" ry="8" filter="url(#dropShadow)" />'
            f'<text class="node-label" x="0" y="-6">{html.escape(label)}</text>'
            f'<text class="node-sublabel" x="0" y="10">{html.escape(sub)}</text></g>'
        )
    body = '\n        '.join(out)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Singapore Retail Customer 360 - Architecture</title>
<style>
{css}
</style>
</head>
<body>
<div class="diagram-container" id="diagramContainer">
  <header class="diagram-header">
{logo}
    <h1>Singapore Retail Customer 360</h1>
    <span class="diagram-subtitle">{v['subtitle']}</span>
  </header>
  <svg class="diagram-canvas" id="diagramCanvas" viewBox="0 0 1400 700" preserveAspectRatio="xMidYMid meet"
       xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Architecture diagram">
    <defs>
      <marker id="arrowhead-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" fill="#29B5E8">
        <polygon points="0 0, 10 3.5, 0 7" />
      </marker>
      <marker id="arrowhead-orange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" fill="#FF9F36">
        <polygon points="0 0, 10 3.5, 0 7" />
      </marker>
      <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="130%">
        <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000000" flood-opacity="0.08" />
      </filter>
    </defs>
        {body}
  </svg>
  <footer class="diagram-footer">
    <span>Hover nodes for details · scroll to zoom · drag to pan · R reset · F fullscreen</span>
    <span>&copy; 2026 Snowflake Inc. All rights reserved.</span>
  </footer>
</div>
<div class="tooltip" id="tooltip"></div>
<script>
{js}
</script>
</body>
</html>
'''


if __name__ == '__main__':
    for variant in sys.argv[1:] or list(VARIANTS):
        page = render(variant)
        name = f'architecture-{variant}.html'
        for path in (os.path.join(HERE, name), os.path.join(REPO, 'app', 'public', name)):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(page)
            print('wrote', os.path.relpath(path, REPO))
    sys.exit(0)
