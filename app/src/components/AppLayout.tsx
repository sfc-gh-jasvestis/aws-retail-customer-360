'use client';

import { useState, useEffect, ReactNode } from 'react';
import { DemoGuide } from '@/components/DemoGuide';

interface Tab {
  id: string;
  label: string;
  icon?: string;
  content: ReactNode;
}

interface AppLayoutProps {
  title: string;
  subtitle?: string;
  logo?: string;
  tabs: Tab[];
  narrative?: any;
}

export function AppLayout({ title, subtitle, logo, tabs, narrative }: AppLayoutProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id || '');
  const [demoMode, setDemoMode] = useState(false);
  const [timerMode, setTimerMode] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true' && narrative) setDemoMode(true);
    if (params.get('timer') === 'true') setTimerMode(true);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D' && narrative) {
        e.preventDefault();
        setDemoMode((prev) => !prev);
      }
      if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        const currentIdx = tabs.findIndex((t) => t.id === activeTab);
        if (currentIdx < tabs.length - 1) setActiveTab(tabs[currentIdx + 1].id);
      }
      if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        const currentIdx = tabs.findIndex((t) => t.id === activeTab);
        if (currentIdx > 0) setActiveTab(tabs[currentIdx - 1].id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, tabs, narrative]);

  return (
    <div className={`min-h-screen bg-slate-50 ${demoMode ? 'pr-80' : ''}`}>
      <header className="border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {logo && <img src={logo} alt="" className="h-8" />}
            <div>
              <h1 className="text-lg font-bold text-slate-900">{title}</h1>
              {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
            </div>
          </div>
          <div className="flex items-center gap-4">
{!demoMode && (
              <button
                onClick={() => setDemoMode(true)}
                className="hidden text-xs text-slate-300 hover:text-slate-500"
                title="Ctrl+Shift+D"
              >
                Demo
              </button>
            )}
          </div>
        </div>
      </header>

      <nav className="border-b border-slate-200 bg-white px-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-snowflake-blue text-snowflake-blue'
                  : 'border-transparent text-slate-600 hover:text-slate-800'
              }`}
            >
              {tab.icon && <span className="mr-1.5">{tab.icon}</span>}
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="p-6">
        {tabs.find((t) => t.id === activeTab)?.content}
      </main>

      {narrative && (
        <DemoGuide
          narrative={narrative}
          activeTab={activeTab}
          visible={demoMode}
          onClose={() => setDemoMode(false)}
          timerMode={timerMode}
        />
      )}
    </div>
  );
}
