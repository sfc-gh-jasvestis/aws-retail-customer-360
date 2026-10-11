'use client';

import { useState } from 'react';

interface FlowNode {
  id: string;
  label: string;
  type: 'source' | 'ingestion' | 'snowflake' | 'output';
  awsOnly?: boolean;
}

interface FlowEdge {
  from: string;
  to: string;
}

interface ArchitectureDiagramProps {
  title?: string;
  // Optional so a page can render the diagram without restating the stack.
  snowflakeFeatures?: string[];
  awsServices?: { name: string; role: string }[];
  nodes?: FlowNode[];
  edges?: FlowEdge[];
}

const DEFAULT_NODES: FlowNode[] = [
  { id: 'kinesis', label: 'Amazon Kinesis', type: 'source', awsOnly: true },
  { id: 's3', label: 'Amazon S3', type: 'source', awsOnly: true },
  { id: 'snowpipe', label: 'Snowpipe Streaming', type: 'ingestion' },
  { id: 'dt', label: 'Dynamic Tables', type: 'snowflake' },
  { id: 'ml', label: 'ML Functions', type: 'snowflake' },
  { id: 'search', label: 'Cortex Search', type: 'snowflake' },
  { id: 'sv', label: 'Semantic View', type: 'snowflake' },
  { id: 'agent', label: 'Cortex Agent', type: 'snowflake' },
  { id: 'app', label: 'React App (SPCS)', type: 'output' },
  { id: 'qs', label: 'QuickSight + Q', type: 'output', awsOnly: true },
  { id: 'sns', label: 'SNS Alerts', type: 'output', awsOnly: true },
];

const DEFAULT_EDGES: FlowEdge[] = [
  { from: 'kinesis', to: 'snowpipe' },
  { from: 's3', to: 'snowpipe' },
  { from: 'snowpipe', to: 'dt' },
  { from: 'dt', to: 'ml' },
  { from: 'dt', to: 'search' },
  { from: 'dt', to: 'sv' },
  { from: 'sv', to: 'agent' },
  { from: 'search', to: 'agent' },
  { from: 'agent', to: 'app' },
  { from: 'dt', to: 'app' },
  { from: 'ml', to: 'app' },
  { from: 'dt', to: 'qs' },
  { from: 'ml', to: 'sns' },
];

const DEFAULT_SNOWFLAKE_FEATURES = [
  'Dynamic Tables (incremental refresh)',
  'ML Functions (Forecast + Anomaly)',
  'Cortex Search + Agent',
  'Semantic View + Intelligence',
  'Alerts + Notifications',
];

const DEFAULT_AWS_SERVICES = [
  { name: 'Amazon S3', role: 'Source Documents' },
  { name: 'Amazon Kinesis', role: 'Streaming Ingest' },
  { name: 'Amazon SNS', role: 'Alerting' },
  { name: 'Amazon QuickSight + Q', role: 'BI Consumption' },
];

export function ArchitectureDiagram({
  title = 'Architecture',
  snowflakeFeatures = DEFAULT_SNOWFLAKE_FEATURES,
  awsServices = DEFAULT_AWS_SERVICES,
  nodes = DEFAULT_NODES,
  edges = DEFAULT_EDGES,
}: ArchitectureDiagramProps) {
  const [mode, setMode] = useState<'snowflake' | 'full'>('full');

  const filteredNodes = mode === 'snowflake' ? nodes.filter((n) => !n.awsOnly) : nodes;
  const filteredEdges = edges.filter((e) => {
    const fromNode = filteredNodes.find((n) => n.id === e.from);
    const toNode = filteredNodes.find((n) => n.id === e.to);
    return fromNode && toNode;
  });

  // Layout: position nodes in columns
  const sources = filteredNodes.filter((n) => n.type === 'source');
  const ingestion = filteredNodes.filter((n) => n.type === 'ingestion');
  const sfNodes = filteredNodes.filter((n) => n.type === 'snowflake');
  const outputs = filteredNodes.filter((n) => n.type === 'output');

  const W = 900;
  const H = 420;
  const colX = [70, 250, 500, 780];

  function getNodePos(node: FlowNode): [number, number] {
    let col: FlowNode[];
    let x: number;
    if (node.type === 'source') { col = sources; x = colX[0]; }
    else if (node.type === 'ingestion') { col = ingestion; x = colX[1]; }
    else if (node.type === 'snowflake') { col = sfNodes; x = colX[2]; }
    else { col = outputs; x = colX[3]; }
    const idx = col.indexOf(node);
    const total = col.length;
    const spacing = Math.min(70, (H - 80) / Math.max(total, 1));
    const startY = (H - (total - 1) * spacing) / 2;
    return [x, startY + idx * spacing];
  }

  function nodeColor(node: FlowNode): string {
    if (node.awsOnly) return '#F97316';
    if (node.type === 'snowflake' || node.type === 'ingestion') return '#29B5E8';
    if (node.type === 'output' && !node.awsOnly) return '#6366F1';
    return '#64748B';
  }

  function nodeBg(node: FlowNode): string {
    if (node.awsOnly) return '#FFF7ED';
    if (node.type === 'snowflake' || node.type === 'ingestion') return '#F0F9FF';
    if (node.type === 'output') return '#EEF2FF';
    return '#F8FAFC';
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          <div className="flex gap-2">
            <button
              className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${mode === 'snowflake' ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              onClick={() => setMode('snowflake')}
            >
              Snowflake Only
            </button>
            <button
              className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${mode === 'full' ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              onClick={() => setMode('full')}
            >
              Full AWS + Snowflake
            </button>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 420 }}>
          <defs>
            <marker id="arrowBlue" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#29B5E8" />
            </marker>
            <marker id="arrowOrange" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#F97316" />
            </marker>
            <marker id="arrowIndigo" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#6366F1" />
            </marker>
          </defs>

          {/* Snowflake platform box */}
          {(() => {
            const sfAll = [...ingestion, ...sfNodes];
            if (sfAll.length === 0) return null;
            const positions = sfAll.map(getNodePos);
            const minX = Math.min(...positions.map((p) => p[0])) - 60;
            const maxX = Math.max(...positions.map((p) => p[0])) + 60;
            const minY = Math.min(...positions.map((p) => p[1])) - 35;
            const maxY = Math.max(...positions.map((p) => p[1])) + 35;
            return (
              <g>
                <rect x={minX} y={minY} width={maxX - minX} height={maxY - minY} rx="12" fill="#F0F9FF" stroke="#29B5E8" strokeWidth="1.5" strokeDasharray="6 3" opacity="0.5" />
                <text x={minX + 8} y={minY + 16} fontSize="11" fill="#0284C7" fontWeight="600">Snowflake</text>
              </g>
            );
          })()}

          {/* Edges */}
          {filteredEdges.map((edge, i) => {
            const fromNode = filteredNodes.find((n) => n.id === edge.from)!;
            const toNode = filteredNodes.find((n) => n.id === edge.to)!;
            const [x1, y1] = getNodePos(fromNode);
            const [x2, y2] = getNodePos(toNode);
            const isAws = fromNode.awsOnly || toNode.awsOnly;
            const marker = isAws ? 'url(#arrowOrange)' : toNode.type === 'output' && !toNode.awsOnly ? 'url(#arrowIndigo)' : 'url(#arrowBlue)';
            const color = isAws ? '#F97316' : toNode.type === 'output' && !toNode.awsOnly ? '#6366F1' : '#29B5E8';
            const dx = x2 - x1;
            const mx = x1 + dx * 0.5;
            const dy = (y2 - y1) * 0.15;
            return (
              <path
                key={i}
                d={`M${x1 + 55},${y1} C${mx},${y1 + dy} ${mx},${y2 - dy} ${x2 - 55},${y2}`}
                fill="none"
                stroke={color}
                strokeWidth="1.5"
                strokeDasharray="4 2"
                markerEnd={marker}
                opacity="0.6"
              />
            );
          })}

          {/* Nodes */}
          {filteredNodes.map((node) => {
            const [x, y] = getNodePos(node);
            const color = nodeColor(node);
            const bg = nodeBg(node);
            return (
              <g key={node.id}>
                <rect x={x - 52} y={y - 18} width="104" height="36" rx="6" fill={bg} stroke={color} strokeWidth="1.5" />
                <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle" fontSize="10" fill={color} fontWeight="600">
                  {node.label.length > 16 ? node.label.slice(0, 15) + '...' : node.label}
                </text>
              </g>
            );
          })}

          {/* Column labels */}
          {sources.length > 0 && <text x={colX[0]} y={H - 10} textAnchor="middle" fontSize="9" fill="#94A3B8" fontWeight="500">DATA SOURCES</text>}
          <text x={colX[1]} y={H - 10} textAnchor="middle" fontSize="9" fill="#94A3B8" fontWeight="500">INGESTION</text>
          <text x={colX[2]} y={H - 10} textAnchor="middle" fontSize="9" fill="#94A3B8" fontWeight="500">AI / ML / ANALYTICS</text>
          <text x={colX[3]} y={H - 10} textAnchor="middle" fontSize="9" fill="#94A3B8" fontWeight="500">OUTPUTS</text>
        </svg>
      </div>

      {/* Feature details below */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4">
          <h3 className="text-sm font-bold text-sky-800">Snowflake Capabilities</h3>
          <ul className="mt-2 space-y-1 text-sm text-sky-700">
            {snowflakeFeatures.map((f, i) => <li key={i}>• {f}</li>)}
          </ul>
        </div>
        {mode === 'full' && awsServices.length > 0 && (
          <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
            <h3 className="text-sm font-bold text-orange-800">AWS Services</h3>
            <ul className="mt-2 space-y-1 text-sm text-orange-700">
              {awsServices.map((s, i) => <li key={i}>• {s.name} — {s.role}</li>)}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
