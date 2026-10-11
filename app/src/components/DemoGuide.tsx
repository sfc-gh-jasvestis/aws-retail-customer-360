'use client';

import { useState, useEffect } from 'react';

interface TabNarrative {
  id: string;
  persona: { name: string; role: string; avatar: string };
  talking_points: string[];
  show: string[];
  call_out: string;
  transition: { next_tab: string; line: string };
}

interface DemoNarrative {
  title: string;
  duration: string;
  thesis: string;
  tabs: TabNarrative[];
}

interface DemoGuideProps {
  narrative: DemoNarrative;
  activeTab: string;
  visible: boolean;
  onClose: () => void;
  timerMode?: boolean;
}

export function DemoGuide({ narrative, activeTab, visible, onClose, timerMode = false }: DemoGuideProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!timerMode || !visible) return;
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [timerMode, visible]);

  if (!visible) return null;

  const currentTab = narrative.tabs.find((t) => t.id === activeTab);
  if (!currentTab) return null;

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className="fixed right-0 top-0 z-50 h-full w-80 overflow-y-auto border-l border-slate-200 bg-white shadow-xl">
      <div className="sticky top-0 border-b border-slate-200 bg-snowflake-dark p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎤</span>
            <span className="text-sm font-bold text-white">DEMO GUIDE</span>
          </div>
          <div className="flex items-center gap-2">
            {timerMode && (
              <span className="rounded bg-red-500 px-2 py-0.5 text-xs font-mono text-white">
                {formatTime(elapsed)}
              </span>
            )}
            <button onClick={onClose} className="text-slate-300 hover:text-white">✕</button>
          </div>
        </div>
        <p className="mt-1 text-xs text-slate-300">{narrative.title} ({narrative.duration})</p>
      </div>

      <div className="p-4 space-y-4">
        <div className="rounded bg-blue-50 p-3">
          <p className="text-xs font-medium text-blue-600">PERSONA</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-800">
            {currentTab.persona.avatar} {currentTab.persona.name}
          </p>
          <p className="text-xs text-slate-600">{currentTab.persona.role}</p>
        </div>

        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">SAY:</p>
          <ul className="mt-1 space-y-2">
            {currentTab.talking_points.map((point, i) => (
              <li key={i} className="rounded border-l-2 border-snowflake-blue bg-slate-50 p-2 text-sm text-slate-700 italic">
                "{point}"
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">SHOW:</p>
          <ul className="mt-1 space-y-1">
            {currentTab.show.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="text-snowflake-accent">→</span> {action}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded bg-amber-50 border border-amber-200 p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-amber-600">CALL OUT:</p>
          <p className="mt-0.5 text-sm font-bold text-slate-800">{currentTab.call_out}</p>
        </div>

        <div className="rounded bg-slate-50 border border-slate-200 p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">TRANSITION:</p>
          <p className="mt-0.5 text-sm text-slate-700">→ Next: <strong>{currentTab.transition.next_tab}</strong></p>
          <p className="mt-1 text-sm italic text-slate-600">"{currentTab.transition.line}"</p>
        </div>
      </div>

      <div className="sticky bottom-0 border-t border-slate-200 bg-slate-50 p-3">
        <p className="text-xs text-slate-500 italic">"{narrative.thesis}"</p>
      </div>
    </div>
  );
}
