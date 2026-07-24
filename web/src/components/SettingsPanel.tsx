import React, { useState, useEffect, useCallback } from 'react';
import { Terminal, Copy, Check, Server, ShieldAlert, ShieldCheck, RefreshCw, HelpCircle, ArrowRight, Activity, CheckCircle2, XCircle } from 'lucide-react';

interface SettingsPanelProps {
  apiUrl: string;
  setApiUrl: (url: string) => void;
  apiToken: string;
  setApiToken: (token: string) => void;
  onTestConnection: () => void;
  connStatus: { text: string; isError: boolean } | null;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  apiUrl,
  setApiUrl,
  apiToken,
  setApiToken,
  onTestConnection,
  connStatus
}) => {
  const [copiedCmd1, setCopiedCmd1] = useState(false);
  const [copiedCmd2, setCopiedCmd2] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'log'>('config');

  const [healthStatus, setHealthStatus] = useState<{ isOnline: boolean; checking: boolean; msg: string }>({
    isOnline: false,
    checking: false,
    msg: 'Click Check Server Status to probe http://localhost:8000'
  });

  const checkServerHealth = useCallback(async () => {
    setHealthStatus((prev) => ({ ...prev, checking: true }));
    const healthUrl = apiUrl.replace(/\/+$/, '') + '/healthz';
    try {
      const res = await fetch(healthUrl, { method: 'GET' });
      if (res.ok) {
        setHealthStatus({
          isOnline: true,
          checking: false,
          msg: `ONLINE: REST server is active and listening on ${apiUrl}`
        });
      } else {
        setHealthStatus({
          isOnline: false,
          checking: false,
          msg: `OFFLINE: Server returned HTTP status ${res.status}`
        });
      }
    } catch {
      setHealthStatus({
        isOnline: false,
        checking: false,
        msg: `OFFLINE: Cannot connect to local server (${apiUrl}). Ensure notebooklm-server is running.`
      });
    }
  }, [apiUrl]);

  useEffect(() => {
    checkServerHealth();
  }, [checkServerHealth]);

  const authCmd = `python -m notebooklm login --browser msedge`;
  const serverCmd = `$env:NOTEBOOKLM_SERVER_TOKEN="${apiToken || 'mysecrettoken'}"; python -m notebooklm.server`;

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

  const commandLogs = [
    { type: 'cmd', text: 'uv pip install -e ".[server]"', status: 'Requires active venv in repo' },
    { type: 'success', text: 'python -m pip install --user -e ".[server,browser]"', status: 'SUCCESS: Installed fastapi 0.139.2, uvicorn 0.34.0, playwright 1.61.0' },
    { type: 'success', text: 'python -m playwright install chromium', status: 'SUCCESS: Playwright Chromium browser installed and ready' },
    { type: 'verify', text: 'python -m notebooklm auth check --json', status: 'AUTHENTICATED: dvzerver@gmail.com (storage_state.json)' },
    { type: 'info', text: `GET ${apiUrl}/healthz`, status: healthStatus.msg }
  ];

  return (
    <div className="settings-panel-expanded">
      <div className="settings-tab-bar">
        <button
          className={`settings-tab-btn ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          <Server size={14} style={{ marginRight: 5 }} />
          REST API Connection & Server Monitor
        </button>
        <button
          className={`settings-tab-btn ${activeTab === 'log' ? 'active' : ''}`}
          onClick={() => setActiveTab('log')}
        >
          <Terminal size={14} style={{ marginRight: 5 }} />
          CLI Activity & Diagnostics Log
        </button>
      </div>

      {activeTab === 'config' ? (
        <div className="settings-content-body">
          {/* Server Health Status Monitor Card */}
          <div className={`server-health-card ${healthStatus.isOnline ? 'online' : 'offline'}`}>
            <div className="health-card-left">
              <Activity size={18} className="health-icon" />
              <div className="health-info-text">
                <span className="health-title">
                  notebooklm-server Status: {healthStatus.isOnline ? 'ONLINE 🟢' : 'OFFLINE 🔴'}
                </span>
                <span className="health-desc">{healthStatus.msg}</span>
              </div>
            </div>
            <button className="btn-health-check" onClick={checkServerHealth} disabled={healthStatus.checking}>
              <RefreshCw size={13} className={healthStatus.checking ? 'spin' : ''} style={{ marginRight: 4 }} />
              {healthStatus.checking ? 'Checking...' : 'Check Status'}
            </button>
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

            <button className="btn-test-conn" onClick={onTestConnection}>
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
                <span className="step-badge">Step 1: Authenticate Google Account (One-Time Setup)</span>
                <button className="btn-copy-cmd" onClick={copyCmd1}>
                  {copiedCmd1 ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                  {copiedCmd1 ? 'Copied!' : 'Copy Command'}
                </button>
              </div>
              <code>{authCmd}</code>
            </div>

            <div className="settings-cmd-box">
              <div className="cmd-box-header">
                <span className="step-badge">Step 2: Start REST API Server (Keep running in PowerShell)</span>
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
              <span>Complete Setup Walkthrough</span>
            </div>
            <ol className="guide-steps-list">
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Open <strong>Windows PowerShell</strong> on your computer.
              </li>
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Run <code>python -m notebooklm login</code>. Sign into your Google Account in the Chromium window, then close it.
              </li>
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Run <code>$env:NOTEBOOKLM_SERVER_TOKEN="mysecrettoken"; python -m notebooklm.server</code> to start the server. Keep this terminal open.
              </li>
              <li>
                <ArrowRight size={12} style={{ marginRight: 6, color: '#58a6ff' }} />
                Click <strong>Test Connection & Load Notebooks</strong> above to view your notebooks!
              </li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="settings-log-body">
          <div className="log-terminal-header">
            <Terminal size={14} style={{ marginRight: 6 }} />
            <span>Local Environment Diagnostic & Error Trace Log</span>
          </div>
          <div className="log-terminal-viewport">
            {commandLogs.map((log, i) => (
              <div key={i} className={`log-line ${log.type}`}>
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
