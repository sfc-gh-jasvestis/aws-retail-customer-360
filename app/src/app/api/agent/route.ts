import { NextResponse } from 'next/server';
import { databaseName, restAuth } from '@/lib/snowflake';

export const dynamic = 'force-dynamic';

// Proxies one question to the Cortex Agent APP.CUSTOMER360_AGENT, which uses
// Cortex Analyst over APP.CUSTOMER360_ANALYTICS and Cortex Search over SOPs.
// The SSE stream is collected server-side and returned with the generated SQL
// and SOP citations so the UI can show how each answer was grounded.
export async function POST(req: Request) {
  let question = '';
  try {
    const body = await req.json();
    question = typeof body?.question === 'string' ? body.question.trim().slice(0, 2000) : '';
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
  if (!question) return NextResponse.json({ error: 'Question required' }, { status: 400 });
  const db = databaseName();
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(db)) return NextResponse.json({ error: 'Database not configured' }, { status: 503 });

  try {
    const { baseUrl, headers } = restAuth();
    const res = await fetch(`${baseUrl}/api/v2/databases/${db}/schemas/APP/agents/CUSTOMER360_AGENT:run`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ messages: [{ role: 'user', content: [{ type: 'text', text: question }] }] }),
    });
    if (!res.ok || !res.body) {
      console.error('agent http', res.status, await res.text().catch(() => ''));
      return NextResponse.json({ error: 'Agent unavailable' }, { status: 503 });
    }
    const text: string[] = [];
    const sql: string[] = [];
    const sops: string[] = [];
    const tools: string[] = [];
    let event = '';
    let buffer = '';
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) {
          let d: any;
          try { d = JSON.parse(line.slice(5)); } catch { continue; }
          if (event === 'response.text.delta') text.push(d.text ?? '');
          else if (event === 'response.tool_use' && d.name) tools.push(d.name);
          else if (event === 'response.tool_result') {
            for (const c of d.content ?? []) {
              if (c.json?.sql) sql.push(c.json.sql);
              for (const r of c.json?.search_results ?? []) {
                const cite = r.doc_title ? `${r.doc_id ?? ''} ${r.doc_title}`.trim() : r.doc_id;
                if (cite && !sops.includes(cite)) sops.push(cite);
              }
            }
          } else if (event === 'error') throw new Error(JSON.stringify(d));
        }
      }
    }
    return NextResponse.json({ answer: text.join('').trim(), sql: sql[0] ?? null, tools, sops, synthetic: true });
  } catch (err) {
    console.error('agent route failed', err);
    return NextResponse.json({ error: 'Agent unavailable' }, { status: 503 });
  }
}
