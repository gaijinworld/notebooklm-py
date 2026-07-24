import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Terminal, Copy, Check, Server, ShieldAlert, ShieldCheck, RefreshCw, HelpCircle, ArrowRight, Activity, Trash2, UserCheck, Play } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

interface SettingsPanelProps {
  apiUrl: string;
  setApiUrl: (url: string) => void;
  apiToken: string;
  setApiToken: (token: string) => void;
  onTestConnection: () => void;
  connStatus: { text: string; isError: boolean } | null;
}

interface LogItem {
  time: string;
  type: 'cmd' | 'success' | 'verify' | 'error' | 'action' | 'info';
  text: string;
  status: string;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  apiUrl,
  setApiUrl,
  apiToken,
  setApiToken,
  onTestConnection,
  connStatus
}) => {
  const { user } = useAuth();
  const userEmail = user?.email || 'default';
  const profileName = userEmail;

  const [copiedCmd1, setCopiedCmd1] = useState(false);
  const [copiedCmd2, setCopiedCmd2] = useState(false);
  const [startingServer, setStartingServer] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'log'>('config');

  const getTimeString = () => new Date().toLocaleTimeString();

  const [logs, setLogs] = useState<LogItem[]>([
    { time: getTimeString(), type: 'info', text: `PROFILE BINDING`, status: `Bound to signed-in user: ${userEmail}` }
  ]);

  const viewportRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((type: LogItem['type'], text: string, status: string) => {
    setLogs((prev) => [
      ...prev,
      { time: new Date().toLocaleTimeString(), type, text, status }
    ]);
  }, []);

  const [healthStatus, setHealthStatus] = useState<{ isOnline: boolean; checking: boolean; msg: string }>({
    isOnline: false,
    checking: false,
    msg: 'Probing local server status...'
  });

  const checkServerHealth = useCallback(async () => {
    setHealthStatus((prev) => ({ ...prev, checking: true }));
    const healthUrl = apiUrl.replace(/\/+$/, '') + '/healthz';
    const startTime = performance.now();
    try {
      const res = await fetch(healthUrl, { method: 'GET' });
      const elapsed = Math.round(performance.now() - startTime);
      if (res.ok) {
        const msg = `ONLINE: REST server active at ${apiUrl} (${elapsed}ms)`;
        setHealthStatus({ isOnline: true, checking: false, msg });
        addLog('info', `GET ${healthUrl}`, `200 OK (${elapsed}ms)`);
      } else {
        const msg = `OFFLINE: Server returned HTTP status ${res.status}`;
        setHealthStatus({ isOnline: false, checking: false, msg });
        addLog('error', `GET ${healthUrl}`, `HTTP ${res.status}`);
      }
    } catch {
      const msg = `OFFLINE: Cannot connect to ${apiUrl}. Ensure notebooklm-server is running.`;
      setHealthStatus({ isOnline: false, checking: false, msg });
      addLog('error', `GET ${healthUrl}`, 'ERR_CONNECTION_REFUSED');
    }
  }, [apiUrl, addLog]);

  useEffect(() => {
    checkServerHealth();
    const interval = setInterval(() => {
      checkServerHealth();
    }, 10000);
    return () => clearInterval(interval);
  }, [checkServerHealth]);

  useEffect(() => {
    if (connStatus) {
      if (connStatus.isError) {
        addLog('error', `GET ${apiUrl}/v1/notebooks`, connStatus.text);
      } else {
        addLog('success', `GET ${apiUrl}/v1/notebooks`, connStatus.text);
      }
    }
  }, [connStatus, apiUrl, addLog]);

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
    }
  }, [logs]);

  const authCmd = `python -m notebooklm --profile "${userEmail}" login --fresh`;
  const serverCmd = `$env:NOTEBOOKLM_PROFILE="${userEmail}"; $env:NOTEBOOKLM_SERVER_TOKEN="${apiToken || 'mysecrettoken'}"; python -m notebooklm.server`;

  const copyCmd1 = () => {
    navigator.clipboard.writeText(authCmd);
    setCopiedCmd1(true);
    setTimeout(() => setCopiedCmd1(false), 2000);
  };

  const copyCmd2 = () => {
    navigator.clipboard.writeText(serverCmd);
    setCopiedCmd2(true);
    setTimeout(() => setCopiedCmd2(false), 2000);
  };

  const handleStartServer = async () => {
    setStartingServer(true);
    addLog('cmd', 'START SERVER', `Triggering server launch for profile: ${userEmail}...`);

    // --- Step 0: Pre-flight auth check (mirrors SKILL.md diagnosis) ---
    // If the server was previously running but /v1/notebooks returned an auth
    // error, the Google cookies are expired. Kill the stale server and force
    // re-authentication before attempting a restart.
    addLog('info', 'PRE-FLIGHT', 'Checking for stale server process...');
    try {
      const staleCheck = await fetch(apiUrl.replace(/\/+$/, '') + '/v1/notebooks', {
        headers: { 'Authorization': `Bearer ${apiToken || 'mysecrettoken'}` }
      });
      if (staleCheck.status === 401 || staleCheck.status === 403) {
        addLog('error', 'AUTH EXPIRED', 'Stale server detected with expired cookies. Kill old process and re-authenticate.');
        addLog('cmd', 'FIX STEP 1', `Kill any running python processes serving notebooklm-server, then run: python -m notebooklm --profile "${userEmail}" login --fresh`);
        addLog('cmd', 'FIX STEP 2', `Then restart: $env:NOTEBOOKLM_PROFILE="${userEmail}"; $env:NOTEBOOKLM_SERVER_TOKEN="${apiToken || 'mysecrettoken'}"; python -m notebooklm.server --host 127.0.0.1 --port 8000`);
        setStartingServer(false);
        return;
      }
    } catch {
      // Connection refused = server not running, which is expected. Continue.
      addLog('info', 'PRE-FLIGHT', 'No stale server detected (connection refused). Proceeding with launch.');
    }

    try {
      const res = await fetch('/wp-json/notebooklm-py/v1/start-server', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: userEmail, token: apiToken || 'mysecrettoken' })
      });
      const data = await res.json();

      if (data.status === 'auth_required') {
        addLog('error', 'AUTH REQUIRED', data.message);
        if (data.storage_path) addLog('info', 'STORAGE PATH', `Checked: ${data.storage_path}`);
        addLog('cmd', 'RUN LOGIN', `${data.python || 'python'} -m notebooklm --profile "${userEmail}" login --browser msedge`);
        setStartingServer(false);
        return;
      }

      addLog('success', 'START SERVER BRIDGE', `Background launch: ${data.message} (python: ${data.python || 'python'})`);
      if (data.log_file) addLog('info', 'LOG FILE', `Errors logged to: ${data.log_file}`);
    } catch {
      addLog('error', 'START SERVER BRIDGE', 'Failed to call WordPress REST endpoint');
    }

    // Aggressive retry: poll healthz every 2s for up to 30s (15 attempts)
    const healthUrl = apiUrl.replace(/\/+$/, '') + '/healthz';
    for (let i = 0; i < 15; i++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const res = await fetch(healthUrl, { method: 'GET' });
        if (res.ok) {
          addLog('info', `GET ${healthUrl}`, '200 OK — server is online!');
          checkServerHealth();
          break;
        }
      } catch {
        addLog('error', `GET ${healthUrl}`, 'ERR_CONNECTION_REFUSED');
      }
    }
    setStartingServer(false);
  };

  const handleTestConnectionClick = () => {
    addLog('cmd', `TEST CONNECTION [Profile: ${userEmail}]`, `Pinging ${apiUrl}/v1/notebooks...`);
    onTestConnection();
  };

  return (
    <div className="settings-panel-expanded">
      <div className="settings-tab-bar">
        <button
          className={`settings-tab-btn ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          <Server size={14} style={{ marginRight: 5 }} />
          REST API Connection & Profile Sync
        </button>
        <button
          className={`settings-tab-btn ${activeTab === 'log' ? 'active' : ''}`}
          onClick={() => setActiveTab('log')}
        >
          <Terminal size={14} style={{ marginRight: 5 }} />
          CLI Activity & Real-Time Diagnostics Log ({logs.length})
        </button>
      </div>

      {activeTab === 'config' ? (
        <div className="settings-content-body">
          {/* Active User Account & Profile Binding Indicator */}
          <div className="user-profile-sync-badge">
            <UserCheck size={16} color="#3fb950" style={{ marginRight: 6 }} />
            <span>Active Web Account Profile: <strong>{userEmail}</strong> (NOTEBOOKLM_PROFILE="{profileName}")</span>
          </div>

          {/* Server Health Status Monitor Card — click anywhere on the card to Start/Fix */}
          <div
            className={`server-health-card ${healthStatus.isOnline ? 'online' : 'offline'} ${startingServer ? 'starting' : ''}`}
            onClick={handleStartServer}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleStartServer(); }}
            title={healthStatus.isOnline ? 'Click to restart server' : 'Click to start / fix server'}
          >
            <div className="health-card-left">
              <Activity size={18} className="health-icon" />
              <div className="health-info-text">
                <span className="health-title">
                  notebooklm-server Status: {healthStatus.isOnline ? 'ONLINE 🟢' : 'OFFLINE 🔴'}
                </span>
                <span className="health-desc">{healthStatus.msg}</span>
              </div>
            </div>
            <div className="health-card-actions">
              <button className="btn-start-server" onClick={(e) => { e.stopPropagation(); handleStartServer(); }} disabled={startingServer}>
                <Play size={13} style={{ marginRight: 4 }} />
                {startingServer ? 'Launching...' : healthStatus.isOnline ? 'Restart Server' : 'Start / Fix Server'}
              </button>
              <button className="btn-health-check" onClick={(e) => { e.stopPropagation(); checkServerHealth(); }} disabled={healthStatus.checking}>
                <RefreshCw size={13} className={healthStatus.checking ? 'spin' : ''} style={{ marginRight: 4 }} />
                {healthStatus.checking ? 'Checking...' : 'Check Status'}
              </button>
            </div>
          </div>

          <div className="settings-fields-row">
            <div className="settings-field">
              <label htmlFor="apiUrlInput">API Base URL</label>
              <input
                id="apiUrlInput"
                type="text"
                placeholder="http://localhost:8000"
                value={apiUrl}
                onChange={(e) => {
                  setApiUrl(e.target.value);
                  localStorage.setItem('nblm_apiUrl', e.target.value);
                }}
              />
            </div>

            <div className="settings-field">
              <label htmlFor="apiTokenInput">Bearer Token ($env:NOTEBOOKLM_SERVER_TOKEN)</label>
              <input
                id="apiTokenInput"
                type="password"
                placeholder="mysecrettoken"
                value={apiToken}
                onChange={(e) => {
                  setApiToken(e.target.value);
                  localStorage.setItem('nblm_apiToken', e.target.value);
                }}
              />
            </div>

            <button className="btn-test-conn" onClick={handleTestConnectionClick}>
              <RefreshCw size={14} style={{ marginRight: 5 }} />
              Test Connection & Load Notebooks
            </button>
          </div>

          {connStatus && (
            <div className={`conn-status-banner ${connStatus.isError ? 'err' : 'ok'}`}>
              {connStatus.isError ? <ShieldAlert size={16} /> : <ShieldCheck size={16} />}
              <span>{connStatus.text}</span>
            </div>
          )}

          <div className="setup-steps-container">
            <div className="settings-cmd-box">
              <div className="cmd-box-header">
                <span className="step-badge">Step 1: Authenticate Google Account for {userEmail}</span>
                <button className="btn-copy-cmd" onClick={copyCmd1}>
                  {copiedCmd1 ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                  {copiedCmd1 ? 'Copied!' : 'Copy Command'}
                </button>
              </div>
              <code>{authCmd}</code>
            </div>

            <div className="settings-cmd-box">
              <div className="cmd-box-header">
                <span className="step-badge">Step 2: Start REST Server for Profile "{userEmail}"</span>
                <button className="btn-copy-cmd" onClick={copyCmd2}>
                  {copiedCmd2 ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                  {copiedCmd2 ? 'Copied!' : 'Copy Command'}
                </button>
              </div>
              <code>{serverCmd}</code>
            </div>
          </div>

          <div className="setup-help-guide-card">
            <div className="guide-card-title">
              <HelpCircle size={15} color="#58a6ff" style={{ marginRight: 6 }} />
              <span>Multi-Account Switch & Setup Walkthrough</span>
            </div>
            <ol className="guide-steps-list">
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Signing in with <strong>{userEmail}</strong> binds your session to <code>NOTEBOOKLM_PROFILE="{userEmail}"</code>.
              </li>
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Click <strong>Start / Fix Server</strong> above or run Step 1 & Step 2 in PowerShell to start the server.
              </li>
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                When you click <strong>Sign Out</strong> and sign in with a <i>different</i> Google account, the commands will automatically switch to that user's profile!
              </li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="settings-log-body">
          <div className="log-terminal-header">
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Terminal size={14} style={{ marginRight: 6 }} />
              <span>Real-Time CLI Activity & Server Diagnostic Event Stream</span>
            </div>
            <button className="btn-clear-logs" onClick={() => setLogs([])}>
              <Trash2 size={12} style={{ marginRight: 4 }} />
              Clear Log
            </button>
          </div>
          <div className="log-terminal-viewport" ref={viewportRef}>
            {logs.map((log, i) => (
              <div key={i} className={`log-line ${log.type}`}>
                <span className="log-time">[{log.time}]</span>
                <span className="log-prompt">$</span>
                <span className="log-text">{log.text}</span>
                <span className="log-status-tag">{log.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
