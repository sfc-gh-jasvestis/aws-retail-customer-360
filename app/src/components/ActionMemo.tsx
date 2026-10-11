'use client';

import { useState } from 'react';

interface ActionMemoProps {
  persona: { name: string; role: string };
  context: Record<string, any>;
  onGenerate: (persona: string, context: Record<string, any>) => Promise<{ subject: string; body: string; urgency: string; actions: string[] }>;
  onSend?: (memo: { subject: string; body: string }) => Promise<void>;
}

export function ActionMemo({ persona, context, onGenerate, onSend }: ActionMemoProps) {
  const [memo, setMemo] = useState<{ subject: string; body: string; urgency: string; actions: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (loading || sending) return;
    setLoading(true);
    setSent(false);
    setError(null);
    setMemo(null);
    try {
      const result = await onGenerate(persona.name, context);
      setMemo(result);
    } catch {
      setError('Unable to generate a grounded draft. Check the data and AI connection, then retry.');
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!memo || !onSend || sending || loading || sent) return;
    setSending(true);
    setError(null);
    try {
      await onSend({ subject: memo.subject, body: memo.body });
      setSent(true);
    } catch {
      setError('Delivery was not confirmed. Check delivery status before trying again.');
    } finally {
      setSending(false);
    }
  };

  const urgencyColors = {
    HIGH: 'bg-red-100 text-red-700 border-red-200',
    MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
    LOW: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">Action Memo</h3>
          <p className="text-xs text-slate-500">For {persona.name} ({persona.role})</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading || sending}
          className="rounded bg-snowflake-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Generate with AI'}
        </button>
      </div>

      <p className="mb-3 text-xs text-slate-500">AI drafts require human review. Generating a draft does not send it.</p>
      {error && <p role="alert" className="mb-3 text-sm text-red-700">{error}</p>}
      {memo && (
        <div className="space-y-3">
          <div className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${urgencyColors[memo.urgency as keyof typeof urgencyColors] || urgencyColors.MEDIUM}`}>
            {memo.urgency} URGENCY
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Subject</p>
            <p className="text-sm font-semibold text-slate-800">{memo.subject}</p>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Recommended Actions</p>
            <ul className="mt-1 space-y-1">
              {memo.actions.map((action, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 text-snowflake-blue">•</span> {action}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Email Draft</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{memo.body}</p>
          </div>
          {onSend && (
            <button
              onClick={handleSend}
              disabled={sent || sending || loading}
              className={`w-full rounded py-2 text-sm font-medium ${sent ? 'bg-emerald-100 text-emerald-700' : 'bg-snowflake-accent text-white hover:bg-orange-600'}`}
            >
              {sent ? 'Delivery confirmed' : sending ? 'Sending...' : 'Send Action Memo'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
