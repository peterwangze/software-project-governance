import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  AlertTriangle,
  Boxes,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Cloud,
  Code2,
  Database,
  FileCheck2,
  FolderGit2,
  Gauge,
  Globe2,
  Home,
  KeyRound,
  Laptop,
  ListChecks,
  Play,
  Rocket,
  Settings,
  Shield,
  SlidersHorizontal,
  Terminal,
  Wrench
} from 'lucide-react';
import './styles.css';

const localChecks = [
  { label: 'Project root', value: '~/projects/ai-code-assistant', state: 'ready', icon: FolderGit2 },
  { label: 'Governance config', value: '.governance/plan-tracker.md', state: 'ready', icon: ClipboardList },
  { label: 'Evidence store', value: '.governance/evidence-log.md', state: 'ready', icon: Database },
  { label: 'Git hooks', value: '.git/hooks', state: 'ready', icon: KeyRound },
  { label: 'Runtime policy', value: 'standard / always-on', state: 'ready', icon: Shield },
  { label: 'Agent rules', value: 'AGENTS.md', state: 'ready', icon: Code2 }
];

const snapshotItems = [
  { label: 'Gate G11 passed', detail: 'No blocking stage issue', tone: 'success', value: 'Passed', icon: Shield },
  { label: 'Risks open', detail: 'Two tracked boundaries remain', tone: 'warning', value: '2', icon: AlertTriangle },
  { label: 'Evidence fresh', detail: 'Updated in the last session', tone: 'success', value: 'Fresh', icon: FileCheck2 }
];

const evidenceRows = [
  { type: 'Evidence', item: 'REL-035 release closure', status: 'Pass', updated: '2 min ago', tone: 'success' },
  { type: 'Risk', item: 'RISK-037 dynamic lifecycle readiness', status: 'Open', updated: '1 hr ago', tone: 'warning' },
  { type: 'Evidence', item: 'VAL-006 non-game validation', status: 'Partial', updated: 'Today', tone: 'neutral' },
  { type: 'Evidence', item: 'VAL-005 python_game validation', status: 'Partial', updated: 'Today', tone: 'neutral' },
  { type: 'Risk', item: 'RISK-036 marketplace readiness', status: 'Open', updated: '4 days ago', tone: 'warning' }
];

const statusTimeline = [
  { label: 'Bootstrap', value: 'Loaded', tone: 'success' },
  { label: 'Gate', value: 'G11 passed', tone: 'success' },
  { label: 'Hooks', value: 'Installed', tone: 'success' },
  { label: 'Risks', value: '2 open', tone: 'warning' },
  { label: 'Release', value: '0.55.0', tone: 'success' }
];

const advancedRoutes = [
  { label: 'Remote Validation', icon: Globe2, detail: 'External target checks', value: '2 partial' },
  { label: 'Release', icon: Rocket, detail: 'Version gates and tags', value: '0.55.0' },
  { label: 'Maintenance', icon: Wrench, detail: 'Archive, cleanup, repairs', value: 'Ready' }
];

const routeConfig = [
  { id: 'local', label: 'Local Setup', icon: Home },
  { id: 'status', label: 'Status', icon: Gauge },
  { id: 'evidence', label: 'Evidence & Risks', icon: FileCheck2 },
  { id: 'advanced', label: 'Advanced', icon: Boxes }
];

function App() {
  const [activeRoute, setActiveRoute] = useState('local');
  const [advancedRoute, setAdvancedRoute] = useState('Remote Validation');

  const routeTitle = useMemo(() => {
    if (activeRoute === 'advanced') return advancedRoute;
    return routeConfig.find((route) => route.id === activeRoute)?.label ?? 'Local Setup';
  }, [activeRoute, advancedRoute]);

  return (
    <div className="app">
      <Sidebar activeRoute={activeRoute} onRouteChange={setActiveRoute} />
      <main className="workspace">
        <TopBar routeTitle={routeTitle} />
        {activeRoute === 'local' && <LocalSetup onAdvanced={() => setActiveRoute('advanced')} />}
        {activeRoute === 'status' && <StatusPage />}
        {activeRoute === 'evidence' && <EvidencePage />}
        {activeRoute === 'advanced' && (
          <AdvancedPage active={advancedRoute} onChange={setAdvancedRoute} />
        )}
      </main>
      <MobileNav activeRoute={activeRoute} onRouteChange={setActiveRoute} />
    </div>
  );
}

function Sidebar({ activeRoute, onRouteChange }) {
  return (
    <aside className="sidebar">
      <div className="window-dots" aria-hidden="true">
        <span className="dot red" />
        <span className="dot yellow" />
        <span className="dot green" />
      </div>
      <div className="brand">
        <div className="brand-mark">
          <Shield size={24} />
        </div>
        <div>
          <strong>Software Project</strong>
          <span>Governance</span>
        </div>
      </div>
      <nav className="nav" aria-label="Primary">
        {routeConfig.slice(0, 3).map((route) => (
          <NavButton
            key={route.id}
            route={route}
            active={activeRoute === route.id}
            onClick={() => onRouteChange(route.id)}
          />
        ))}
      </nav>
      <div className="nav-group">
        <div className="nav-group-title">Advanced</div>
        <NavButton
          route={routeConfig[3]}
          active={activeRoute === 'advanced'}
          onClick={() => onRouteChange('advanced')}
        />
      </div>
      <div className="sidebar-spacer" />
      <button className="utility-button" type="button">
        <Settings size={18} />
        Settings
      </button>
      <button className="utility-button" type="button">
        <CircleHelp size={18} />
        Help
      </button>
      <div className="local-mode">
        <span className="status-dot success" />
        <div>
          <strong>Local mode</strong>
          <span>All data stays on this machine</span>
        </div>
        <ChevronRight size={17} />
      </div>
    </aside>
  );
}

function NavButton({ route, active, onClick }) {
  const Icon = route.icon;
  return (
    <button className={`nav-button ${active ? 'active' : ''}`} type="button" onClick={onClick}>
      <Icon size={20} />
      <span>{route.label}</span>
    </button>
  );
}

function TopBar({ routeTitle }) {
  return (
    <header className="topbar">
      <div className="project-select">
        <span>Current project</span>
        <button type="button">
          <Laptop size={17} />
          ai-code-assistant
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="top-status">
        <StatusMetric label="Environment" value="Local" tone="success" />
        <StatusMetric label="Governance mode" value="Enforced" tone="success" />
        <StatusMetric label="Last verified" value="2 min ago" tone="success" />
        <button className="secondary-action" type="button">
          <SlidersHorizontal size={17} />
          Project settings
        </button>
      </div>
      <h1>{routeTitle}</h1>
    </header>
  );
}

function StatusMetric({ label, value, tone }) {
  return (
    <div className="status-metric">
      <span>{label}</span>
      <strong>
        <span className={`status-dot ${tone}`} />
        {value}
      </strong>
    </div>
  );
}

function LocalSetup({ onAdvanced }) {
  return (
    <section className="page-grid">
      <div className="content-stack primary-stack">
        <Panel title="Local configuration" action="All local checks passed">
          <div className="check-list">
            {localChecks.map((item) => (
              <CheckRow key={item.label} item={item} />
            ))}
          </div>
          <div className="panel-footer">
            <button className="link-action" type="button">
              <Activity size={17} />
              Re-scan configuration
            </button>
          </div>
        </Panel>
        <EvidenceTable compact={false} />
      </div>
      <div className="content-stack side-stack">
        <SnapshotPanel />
        <EnvironmentPanel />
        <VerifyPanel />
        <Panel title="Advanced" className="quiet-panel">
          <p className="muted">Remote validation, release and maintenance tools.</p>
          <button className="wide-button" type="button" onClick={onAdvanced}>
            Open advanced
            <ChevronRight size={18} />
          </button>
        </Panel>
      </div>
    </section>
  );
}

function StatusPage() {
  return (
    <section className="page-grid status-layout">
      <div className="content-stack primary-stack">
        <SnapshotPanel expanded />
        <Panel title="Governance timeline">
          <div className="timeline">
            {statusTimeline.map((item) => (
              <div className="timeline-row" key={item.label}>
                <span className={`status-dot ${item.tone}`} />
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <div className="content-stack side-stack">
        <VerifyPanel />
        <EnvironmentPanel />
      </div>
    </section>
  );
}

function EvidencePage() {
  return (
    <section className="single-page">
      <EvidenceTable compact={false} />
      <div className="evidence-summary">
        <MetricCard label="Evidence records" value="592" tone="success" />
        <MetricCard label="Open risks" value="2" tone="warning" />
        <MetricCard label="Review coverage" value="100%" tone="success" />
      </div>
    </section>
  );
}

function AdvancedPage({ active, onChange }) {
  const selected = advancedRoutes.find((route) => route.label === active) ?? advancedRoutes[0];
  const SelectedIcon = selected.icon;
  return (
    <section className="advanced-page">
      <div className="advanced-tabs" role="tablist" aria-label="Advanced routes">
        {advancedRoutes.map((route) => {
          const Icon = route.icon;
          return (
            <button
              key={route.label}
              className={active === route.label ? 'selected' : ''}
              type="button"
              onClick={() => onChange(route.label)}
            >
              <Icon size={18} />
              {route.label}
            </button>
          );
        })}
      </div>
      <Panel title={selected.label} className="advanced-panel">
        <div className="advanced-header">
          <div className="large-icon">
            <SelectedIcon size={28} />
          </div>
          <div>
            <p>{selected.detail}</p>
            <strong>{selected.value}</strong>
          </div>
        </div>
        <div className="advanced-list">
          <AdvancedRow label="Remote target" value="python_game / shitu" />
          <AdvancedRow label="Boundary" value="Partial validation only" />
          <AdvancedRow label="Next gate" value="RISK-036 / RISK-037" />
        </div>
      </Panel>
    </section>
  );
}

function Panel({ title, action, className = '', children }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-header">
        <h2>{title}</h2>
        {action && <span className="success-chip">{action}</span>}
      </div>
      {children}
    </section>
  );
}

function CheckRow({ item }) {
  const Icon = item.icon;
  return (
    <div className="check-row">
      <Icon size={18} />
      <span>{item.label}</span>
      <code>{item.value}</code>
      <span className="check-state">
        <Check size={15} />
      </span>
    </div>
  );
}

function SnapshotPanel({ expanded = false }) {
  return (
    <Panel title="Delivery Trust Snapshot" className={expanded ? 'snapshot expanded' : 'snapshot'}>
      <div className="snapshot-list">
        {snapshotItems.map((item) => {
          const Icon = item.icon;
          return (
            <div className="snapshot-row" key={item.label}>
              <Icon className={item.tone} size={26} />
              <div>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
              <span className={`value-chip ${item.tone}`}>{item.value}</span>
            </div>
          );
        })}
      </div>
      <button className="link-row" type="button">
        View full status
        <ChevronRight size={18} />
      </button>
    </Panel>
  );
}

function EnvironmentPanel() {
  const rows = [
    ['OS', 'Windows 11'],
    ['Runtime', 'Node.js 24.13'],
    ['Git', 'master clean'],
    ['Disk', 'Local'],
    ['Connectivity', 'Optional']
  ];
  return (
    <Panel title="Local environment">
      <div className="key-value-list">
        {rows.map(([label, value]) => (
          <div className="key-value" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <button className="link-row" type="button">
        Environment details
        <ChevronRight size={18} />
      </button>
    </Panel>
  );
}

function VerifyPanel() {
  return (
    <Panel title="Verify locally">
      <div className="command-box">
        <Terminal size={17} />
        <code>python ... verify_workflow.py status</code>
      </div>
      <button className="primary-action" type="button">
        <Play size={18} />
        Run checks
      </button>
    </Panel>
  );
}

function EvidenceTable({ compact }) {
  return (
    <Panel title="Recent evidence & risks" className="table-panel">
      <div className="table-header">
        <span>Type</span>
        <span>Item</span>
        <span>Status</span>
        <span>Updated</span>
      </div>
      <div className="table-body">
        {evidenceRows.slice(0, compact ? 3 : evidenceRows.length).map((row) => (
          <div className="table-row" key={row.item}>
            <span>{row.type}</span>
            <strong>{row.item}</strong>
            <span className={`value-chip ${row.tone}`}>{row.status}</span>
            <span>{row.updated}</span>
          </div>
        ))}
      </div>
      <button className="link-row" type="button">
        Open Evidence & Risks
        <ChevronRight size={18} />
      </button>
    </Panel>
  );
}

function MetricCard({ label, value, tone }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function AdvancedRow({ label, value }) {
  return (
    <div className="advanced-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MobileNav({ activeRoute, onRouteChange }) {
  return (
    <nav className="mobile-nav" aria-label="Mobile primary">
      {routeConfig.map((route) => {
        const Icon = route.icon;
        return (
          <button
            key={route.id}
            className={activeRoute === route.id ? 'active' : ''}
            type="button"
            onClick={() => onRouteChange(route.id)}
          >
            <Icon size={19} />
            <span>{route.label.replace(' & Risks', '')}</span>
          </button>
        );
      })}
    </nav>
  );
}

createRoot(document.getElementById('root')).render(<App />);
