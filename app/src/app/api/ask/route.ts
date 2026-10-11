import { NextResponse } from 'next/server';
import { executeQuery } from '@/lib/snowflake';
import { demoPlatform } from '@/lib/platform';

export const dynamic = 'force-dynamic';

// Only these fixed, read-only queries can run. The model never writes SQL; it
// only summarises rows returned here, so every answer is traceable to data.
const INTENTS: Record<string, { match: RegExp; sql: string }> = {
  cohorts: {
    match: /churn|cohort|segment|area|town|worst|highest|unsub/i,
    sql: `SELECT ENTITY_ID, ENTITY_NAME, REGION, SEGMENT, ISSUE_COUNT, CHURNED_COUNT, UNSUBSCRIBE_COUNT, ROUND(ISSUE_CHURN_PCT, 1) AS ISSUE_CHURN_PCT
FROM CURATED.PERFORMANCE_SUMMARY
QUALIFY DENSE_RANK() OVER (ORDER BY CHURNED_COUNT DESC) <= 3
ORDER BY CHURNED_COUNT DESC, ISSUE_COUNT DESC`,
  },
  types: {
    match: /type|reason|cause|why|issue|complaint/i,
    sql: `SELECT ISSUE_TYPE, ISSUE_COUNT, CHURNED_COUNT, UNSUBSCRIBE_COUNT, ROUND(ISSUE_CHURN_PCT, 1) AS ISSUE_CHURN_PCT
FROM CURATED.ISSUE_SUMMARY ORDER BY CHURNED_COUNT DESC LIMIT 8`,
  },
  kpis: {
    match: /.*/,
    sql: `SELECT TITLE, DISPLAY, SOURCE_WATERMARK FROM CURATED.KPI_SUMMARY ORDER BY SORT_ORDER`,
  },
};

const DEFINITIONS =
  'Issue-free purchase rate = purchases without a service issue / purchases made. Issue churn rate = churned members / service issues raised. ' +
  'An unsubscribe is a churned member who also opted out of marketing. Mall checkout outage issues hit every cohort in one planning area and always resolve with the members retained. ' +
  'Values are in SGD; cohorts are aggregate loyalty member groups in 5 Singapore planning areas. All data is synthetic demo data.';

// provider 'cortex' = Snowflake AI_COMPLETE; 'bedrock' = Amazon Bedrock Claude
// via the external-access UDF APP.BEDROCK_GENERATE (aws/setup_aws.py).
async function summarise(question: string, rows: unknown[], provider: 'cortex' | 'bedrock' = 'cortex'): Promise<string> {
  const prompt =
    'You are a customer retention analyst at Kopi Lane Retail, a fictional Singapore omnichannel retailer. Answer ONLY from the JSON rows and definitions below. ' +
    'If the rows do not answer the question, say so. Do not invent numbers. Keep it under 120 words.\n' +
    `Definitions: ${DEFINITIONS}\nRows: ${JSON.stringify(rows)}\nQuestion: ${question}`;
  const out = await executeQuery<{ R: string }>(
    provider === 'bedrock' ? 'SELECT APP.BEDROCK_GENERATE(?) AS R' : `SELECT AI_COMPLETE('claude-sonnet-4-5', ?) AS R`,
    [prompt],
  );
  const raw = String(out[0]?.R ?? '').trim();
  // AI_COMPLETE returns a JSON string literal; decode it when present.
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed === 'string' ? parsed : raw;
  } catch {
    return raw;
  }
}

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
  const question = typeof body?.question === 'string' ? body.question.trim().slice(0, 2000) : '';
  const memo = body?.mode === 'memo';
  if (!memo && !question) return NextResponse.json({ error: 'Question required' }, { status: 400 });

  try {
    if (memo) {
      const provider = demoPlatform() === 'aws' ? 'bedrock' : 'cortex';
      const [kpis, cohorts, types, risk, bands] = await Promise.all([
        executeQuery(INTENTS.kpis.sql),
        executeQuery(INTENTS.cohorts.sql),
        executeQuery(INTENTS.types.sql),
        executeQuery(`SELECT ENTITY_ID, ROUND(CHURN_PROB_7D, 2) AS CHURN_PROB_7D, RISK_BAND
FROM ML.CHURN_RISK_SCORES ORDER BY CHURN_PROB_7D DESC LIMIT 5`),
        executeQuery(`SELECT RISK_BAND, COUNT(*) AS COHORTS FROM ML.CHURN_RISK_SCORES GROUP BY RISK_BAND`),
      ]);
      const rows = { kpis, topChurnedCohorts: cohorts, issueTypes: types, top5ByRisk: risk, cohortsPerRiskBand: bands };
      const answer = await summarise(
        'Draft a short action memo for Wen Hui Chua, Head of Customer Retention at Kopi Lane Retail, with 3 prioritised actions, citing the figures.',
        [rows],
        provider,
      );
      return NextResponse.json({ answer, sources: rows, provider: provider === 'bedrock' ? 'Amazon Bedrock (Claude Sonnet 4.5)' : 'Snowflake Cortex AI_COMPLETE (claude-sonnet-4-5)', draft: true, synthetic: true });
    }
    const key = Object.keys(INTENTS).find((k) => INTENTS[k].match.test(question))!;
    const rows = await executeQuery(INTENTS[key].sql);
    const answer = await summarise(question, rows);
    return NextResponse.json({ answer, sql: INTENTS[key].sql, sources: rows, synthetic: true });
  } catch (err) {
    console.error('ask route failed', err);
    return NextResponse.json({ error: 'AI service unavailable' }, { status: 503 });
  }
}
