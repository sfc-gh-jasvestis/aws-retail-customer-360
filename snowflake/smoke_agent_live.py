"""Smoke-test the Cortex Agent via REST using the local connector session."""
import json
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_core import connect

DB = sys.argv[1]
QUESTION = sys.argv[2] if len(sys.argv) > 2 else 'Which 3 cohorts have the most churned members, and what SOP applies to the top one?'
con = connect(sys.argv[3] if len(sys.argv) > 3 else 'default')
host = con.host
url = f'https://{host}/api/v2/databases/{DB}/schemas/APP/agents/CUSTOMER360_AGENT:run'
body = {'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': QUESTION}]}]}
r = requests.post(url, json=body, stream=True, timeout=300, headers={
    'Authorization': f'Snowflake Token="{con.rest.token}"', 'Accept': 'text/event-stream',
    'Content-Type': 'application/json'})
print('HTTP', r.status_code)
event, text, tools, sql = None, [], [], []
for line in r.iter_lines(decode_unicode=True):
    if line.startswith('event:'):
        event = line[6:].strip()
    elif line.startswith('data:') and event:
        try:
            d = json.loads(line[5:])
        except json.JSONDecodeError:
            continue
        if event == 'response.text.delta':
            text.append(d.get('text', ''))
        elif event == 'response.tool_use':
            tools.append(d.get('name'))
        elif event == 'response.tool_result':
            for c in d.get('content', []):
                j = c.get('json') or {}
                if j.get('sql'):
                    sql.append(j['sql'])
        elif event == 'error':
            print('ERROR', d)
print('TOOLS', tools)
print('SQL', sql[:1])
print('ANSWER', ''.join(text)[:1500])
