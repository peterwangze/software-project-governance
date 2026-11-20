import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardList,
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

const webConsoleCommand = 'python skills/software-project-governance/infra/verify_workflow.py web-console --start';
const webConsoleUrl = 'http://127.0.0.1:5173/';

const routeConfig = [
  { id: 'status', label: 'Work units', icon: Gauge },
  { id: 'local', label: 'Local Setup', icon: Home },
  { id: 'evidence', label: 'Evidence & Risks', icon: FileCheck2 },
  { id: 'advanced', label: 'Advanced', icon: Boxes }
];

const advancedRoutes = [
  { label: 'Remote Validation', icon: Globe2, detail: 'External target checks (dry-run only)', value: 'Partial' },
  { label: 'Release', icon: Rocket, detail: 'Version gates and tags (CLI-managed)', value: 'CLI only' },
  { label: 'Maintenance', icon: Wrench, detail: 'Archive, cleanup, repairs (CLI-managed)', value: 'CLI only' }
];

function App() {
  const [activeRoute, setActiveRoute] = useState('status');
  const [advancedRoute, setAdvancedRoute] = useState('Remote Validation');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const res = await fetch('/api/governance', { cache: 'no-store' });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const json = await res.json();
      setData(json);
      if (json.error) setError(json.error);
    } catch (e) {
      setError(`Cannot reach local API server: ${e.message}. Start it with: python web/server.py`);
      setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const showNotice = useCallback((msg) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 4000);
  }, []);

  const routeTitle = useMemo(() => {
    if (activeRoute === 'advanced') return advancedRoute;
    return routeConfig.find((route) => route.id === activeRoute)?.label ?? 'Local Setup';
  }, [activeRoute, advancedRoute]);

  if (loading) {
    return (
      <div className="app">
        <div className="loading-state">
          <Activity size={28} className="spin" />
          <p>Loading local governance status…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Sidebar
        activeRoute={activeRoute}
        onRouteChange={setActiveRoute}
        onNotice={showNotice}
      />
      <main className="workspace">
        <TopBar routeTitle={routeTitle} data={data} onNotice={showNotice} onRefresh={refresh}
          refreshing={refreshing} onRisks={() => setActiveRoute('evidence')} />
        <MobileNav activeRoute={activeRoute} onRouteChange={setActiveRoute} />
        {error && (
          <div className="error-banner" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
            <button className="link-action" type="button" onClick={refresh}>
              <Activity size={16} /> Retry
            </button>
          </div>
        )}
        {notice && (
          <div className="notice-banner" role="status">
            <CircleHelp size={18} />
            <span>{notice}</span>
          </div>
        )}
        {activeRoute === 'local' && (
          <LocalSetup
            data={data}
            onAdvanced={() => setActiveRoute('advanced')}
            onRefresh={refresh}
            refreshing={refreshing}
            onNavigate={setActiveRoute}
          />
        )}
        {activeRoute === 'status' && <StatusPage data={data} />}
        {activeRoute === 'evidence' && <EvidencePage data={data} />}
        {activeRoute === 'advanced' && (
          <AdvancedPage active={advancedRoute} onChange={setAdvancedRoute} onNotice={showNotice} />
        )}
      </main>
    </div>
  );
}

function Sidebar({ activeRoute, onRouteChange, onNotice }) {
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
      <button
        className="utility-button"
        type="button"
        onClick={() => onNotice('Settings: this is a read-only local dashboard. Project configuration is edited via the CLI (plan-tracker.md) or your agent client.')}
      >
        <Settings size={18} />
        Settings
      </button>
      <button
        className="utility-button"
        type="button"
        onClick={() => onNotice('Help: run /governance in your CLI/agent client for full interactive governance. This Web console is a read-only companion view of local status.')}
      >
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

function TopBar({ routeTitle, data, onNotice, onRefresh, refreshing, onRisks }) {
  const projectName = data?.project_name ?? '—';
  if (routeTitle === 'Work units') {
    const riskCount = data?.open_risks?.length ?? 0;
    return (
      <header className="work-header">
        <span className="muted">{projectName}</span>
        <div className="page-title">
          <h1>{routeTitle}</h1>
          <div className="work-actions">
            {riskCount > 0 && <button className="link-action" type="button" onClick={onRisks}>{riskCount} open risks</button>}
            <button className="link-action" type="button" onClick={onRefresh} disabled={refreshing}>
              <Activity size={16} />{refreshing ? 'Refreshing…' : 'Refresh data'}
            </button>
          </div>
        </div>
      </header>
    );
  }
  return (
    <header className="topbar">
      <div className="project-select">
        <span>Current project</span>
        <button type="button" onClick={() => onNotice(`Project root: ${data?.project_root ?? 'unknown'}`)}>
          <Laptop size={17} />
          {projectName}
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="top-status">
        <StatusMetric label="Environment" value="Local" tone="success" />
        <StatusMetric label="Release" value={data?.release_version ?? '—'} tone="success" />
        <StatusMetric label="Open risks" value={String(data?.open_risks?.length ?? 0)} tone="warning" />
        <button
          className="secondary-action"
          type="button"
          onClick={() => onNotice('Project settings are managed via the CLI (plan-tracker.md, risk-log.md) and your agent client. This dashboard is read-only.')}
        >
          <SlidersHorizontal size={17} />
          Project settings
        </button>
      </div>
      <div className="page-title">
        <h1>{routeTitle}</h1>
      </div>
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

function LocalSetup({ data, onAdvanced, onRefresh, refreshing, onNavigate }) {
  const localChecks = useMemo(() => {
    if (!data) return [];
    return [
      { label: 'Project root', value: data.project_root ?? '—', state: 'ready', icon: FolderGit2 },
      { label: 'Release version', value: data.release_version ?? '—', state: 'ready', icon: Code2 },
      { label: 'Workflow version', value: data.workflow_version ?? '—', state: 'ready', icon: Shield },
      { label: 'Trigger mode', value: data.trigger_mode ?? '—', state: 'ready', icon: Activity },
      { label: 'Permission mode', value: data.permission_mode ?? '—', state: 'ready', icon: KeyRound },
      { label: 'Profile', value: data.profile ?? '—', state: 'ready', icon: ClipboardList },
      { label: 'Governance config', value: '.governance/plan-tracker.md', state: 'ready', icon: ClipboardList },
      { label: 'Evidence store', value: '.governance/evidence-log.md', state: 'ready', icon: Database }
    ];
  }, [data]);

  return (
    <section className="page-grid">
      <div className="content-stack primary-stack">
        <EntryPanel />
        <Panel title="Local configuration" action={data ? `${data.evidence_count ?? 0} evidence records` : 'Loading'}>
          <div className="check-list">
            {localChecks.map((item) => (
              <CheckRow key={item.label} item={item} />
            ))}
          </div>
          <div className="panel-footer">
            <button className="link-action" type="button" onClick={onRefresh} disabled={refreshing}>
              <Activity size={17} className={refreshing ? 'spin' : ''} />
              {refreshing ? 'Re-scanning…' : 'Re-scan configuration'}
            </button>
          </div>
        </Panel>
        <EvidenceTable compact={false} data={data} onNavigate={onNavigate} />
      </div>
      <div className="content-stack side-stack">
        <EnvironmentPanel data={data} />
        <VerifyPanel onRefresh={onRefresh} refreshing={refreshing} />
        <Panel title="Advanced" className="quiet-panel">
          <p className="muted">Remote validation, release and maintenance tools (read-only summary; actions run in CLI).</p>
          <button className="wide-button" type="button" onClick={onAdvanced}>
            Open advanced
            <ChevronRight size={18} />
          </button>
        </Panel>
      </div>
    </section>
  );
}

function EntryPanel() {
  const [copied, setCopied] = useState(null);
  const copyValue = async (value, type) => {
    setCopied(type);
    window.setTimeout(() => setCopied(null), 1800);
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Local dashboard fallback: the command/URL remains visible even if clipboard is blocked.
    }
  };

  return (
    <section className="entry-panel" aria-labelledby="entry-title">
      <div className="entry-copy">
        <span className="entry-source">Opened from CLI / Client</span>
        <h2 id="entry-title">Companion dashboard for local governance status</h2>
        <p>
          Keep task execution, decisions and agent actions in your CLI or client. Use this
          Web console to scan local setup, status, evidence and risks without digging
          through long command output.
        </p>
      </div>
      <div className="entry-actions">
        <div className="entry-command">
          <Terminal size={17} />
          <code>{webConsoleCommand}</code>
        </div>
        <div className="entry-action-row">
          <button
            className="primary-action compact"
            type="button"
            onClick={() => copyValue(webConsoleCommand, 'command')}
          >
            <Play size={18} />
            {copied === 'command' ? 'Command copied' : 'Copy start command'}
          </button>
          <button
            className="secondary-action compact"
            type="button"
            onClick={() => copyValue(webConsoleUrl, 'url')}
          >
            <ArrowUpRight size={17} />
            {copied === 'url' ? 'URL copied' : 'Copy URL'}
          </button>
        </div>
      </div>
    </section>
  );
}

function StatusPage({ data }) {
  const loops = data?.loops;
  const failureTitle = loops?.units?.length ? 'Evidence needs attention' : 'Loop record unavailable';
  return (
    <section className="single-page status-layout">
        {(loops?.state === 'invalid' || !loops?.units?.length) && (
          <Panel title={loops?.state === 'invalid' ? failureTitle : 'No work units'}>
            <p className="muted" role={loops?.state === 'invalid' ? 'alert' : 'status'}>
              {loops?.message ?? 'Loop status unavailable.'}
            </p>
          </Panel>
        )}
        {loops?.units?.map((unit) => <WorkUnit key={unit.flow_unit_id} unit={unit} />)}
    </section>
  );
}

function WorkUnit({ unit }) {
  const blockers = unit.blockers ?? [];
  const review = unit.last_review;
  const returnTo = unit.return_to;
  const evidence = unit.evidence_refs.filter((ref) => ref !== review?.evidence_ref);
  const gateTone = ['failed', 'blocked', 'escalated', 'unverified'].includes(unit.gate_status) ? 'warning' : 'neutral';
  return (
    <article className="panel work-unit">
      <header className="unit-heading">
        <div className="unit-identity">
          <span>{unit.active_loop_tier ? `${unit.active_loop_tier} loop` : unit.runtime_status} · round {unit.loop_count}</span>
          <h2>{unit.title || unit.flow_unit_id}</h2>
          <code>{unit.flow_unit_id}{unit.parent_unit_id && ` · parent ${unit.parent_unit_id}`}</code>
        </div>
      </header>
      <dl className="unit-facts">
        {unit.goal && unit.goal !== unit.title && <><dt>Goal</dt><dd>{unit.goal}</dd></>}
        {unit.acceptance && <><dt>Acceptance</dt><dd>{unit.acceptance}</dd></>}
        <dt>Next action</dt><dd>{unit.next_action}</dd>
        <dt>Local gate</dt><dd><span className={`value-chip ${gateTone}`}>{unit.gate_id} · {unit.gate_status}</span></dd>
        {returnTo && <><dt>Return after rework</dt><dd>{returnTo.tier} loop · {returnTo.gate} · round {returnTo.loop_count}</dd></>}
        {unit.previous_unit_id && <><dt>Previous iteration</dt><dd>{unit.previous_unit_id}
          {unit.previous_review ? <> · {unit.previous_review.gate} · round {unit.previous_review.iteration} · {unit.previous_review.result}<br />{unit.previous_review.evidence_ref}</> : ' · acceptance unverified'}
        </dd></>}
        {review ? <><dt>{unit.state === 'invalid' ? 'Recorded decision (unverified)' : 'Last review'}</dt><dd>{review.gate} · round {review.iteration} · {review.result}<br />{review.evidence_ref}</dd></>
          : unit.last_gate_result && <><dt>Last decision</dt><dd>{unit.last_gate_result}</dd></>}
        {blockers.length > 0 && <><dt>Blocked by</dt><dd>{blockers.join(', ')}</dd></>}
        {unit.waiting_on.length > 0 && <><dt>Waiting on</dt><dd>{unit.waiting_on.join(', ')}</dd></>}
        {unit.open_children.length > 0 && <><dt>Open child units</dt><dd>{unit.open_children.join(', ')}</dd></>}
        {evidence.length > 0 && <><dt>Evidence</dt><dd>{evidence.join(', ')}</dd></>}
      </dl>
    </article>
  );
}

function EvidencePage({ data }) {
  return (
    <section className="single-page">
      <EvidenceTable compact={false} data={data} />
      <div className="evidence-summary">
        <MetricCard label="Evidence records" value={String(data?.evidence_count ?? 0)} tone="success" />
        <MetricCard label="Open risks" value={String(data?.open_risks?.length ?? 0)} tone="warning" />
      </div>
      {(data?.open_risks?.length ?? 0) > 0 && (
        <Panel title="Open risks">
          <div className="timeline">
            {data.open_risks.map((r) => (
              <div className="timeline-row" key={r.id}>
                <span className="status-dot warning" />
                <span>{r.id}</span>
                <strong>{r.deadline ? `deadline ${r.deadline}` : 'open'} · {r.description.slice(0, 60)}</strong>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </section>
  );
}

function AdvancedPage({ active, onChange, onNotice }) {
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
          <AdvancedRow label="Execution surface" value="CLI / agent client (not this dashboard)" />
          <AdvancedRow label="Boundary" value="Read-only summary here; actions run in CLI" />
        </div>
        <div className="panel-footer">
          <button
            className="link-action"
            type="button"
            onClick={() => onNotice('Advanced actions (release, archive, remote validation) are run from the CLI. This dashboard only summarizes their status.')}
          >
            <CircleHelp size={17} />
            Why CLI only?
          </button>
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
      <code>{String(item.value).length > 60 ? `${String(item.value).slice(0, 57)}…` : item.value}</code>
      <span className="check-state">
        <Check size={15} />
      </span>
    </div>
  );
}

function EnvironmentPanel({ data }) {
  const rows = useMemo(() => {
    const base = [
      ['Project root', data?.project_root ?? '—'],
      ['Project name', data?.project_name ?? '—'],
      ['Trigger mode', data?.trigger_mode ?? '—'],
      ['Permission mode', data?.permission_mode ?? '—'],
      ['Profile', data?.profile ?? '—']
    ];
    return base;
  }, [data]);
  return (
    <Panel title="Local environment">
      <div className="key-value-list">
        {rows.map(([label, value]) => (
          <div className="key-value" key={label}>
            <span>{label}</span>
            <strong>{String(value).length > 50 ? `${String(value).slice(0, 47)}…` : value}</strong>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function VerifyPanel({ onRefresh, refreshing }) {
  return (
    <Panel title="Verify locally">
      <div className="command-box">
        <Terminal size={17} />
        <code>python ... verify_workflow.py loop status</code>
      </div>
      <div className="command-box secondary-command">
        <Terminal size={17} />
        <code>python ... verify_workflow.py web-console --status</code>
      </div>
      <button className="primary-action" type="button" onClick={onRefresh} disabled={refreshing}>
        <Activity size={18} className={refreshing ? 'spin' : ''} />
        {refreshing ? 'Refreshing…' : 'Refresh data'}
      </button>
    </Panel>
  );
}

function EvidenceTable({ compact, data, onNavigate }) {
  const rows = data?.recent_evidence ?? [];
  return (
    <Panel title="Recent evidence & risks" className="table-panel">
      <div className="table-header">
        <span>ID</span>
        <span>Task</span>
        <span>Status</span>
        <span>Date</span>
      </div>
      <div className="table-body">
        {rows.slice(0, compact ? 3 : rows.length).map((row) => (
          <div className="table-row" key={row.id}>
            <span>{row.id}</span>
            <strong>{row.task}</strong>
            <span className={`value-chip ${row.status === '完成' || row.status === 'Pass' ? 'success' : 'neutral'}`}>{row.status}</span>
            <span>{row.date}</span>
          </div>
        ))}
        {rows.length === 0 && <p className="muted">No recent evidence.</p>}
      </div>
      {onNavigate && <button className="link-row" type="button" onClick={() => onNavigate('evidence')}>
        Open Evidence & Risks
        <ChevronRight size={18} />
      </button>}
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
