import React, { useState } from 'react';
import { Terminal, Copy, Check, Server, ShieldAlert, ShieldCheck, AlertCircle, RefreshCw, KeyRound } from 'lucide-react';

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

  const authCmd = `python -m notebooklm login`;
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
    { type: 'verify', text: 'python -m notebooklm auth check --json', status: 'STATUS: Pending Google login (storage_state.json)' },
    { type: 'action', text: 'READY FOR LOGIN', status: 'Run "python -m notebooklm login" in PowerShell to sign in once' },
    { type: 'info', text: `GET ${apiUrl}/healthz`, status: connStatus ? connStatus.text : 'Awaiting connection test...' }
  ];

  return (
    <div className="settings-panel-expanded">
      <div className="settings-tab-bar">
        <button
          className={`settings-tab-btn ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          <Server size={14} style={{ marginRight: 5 }} />
          REST API Connection & Environment
        </button>
        <button
          className={`settings-tab-btn ${activeTab === 'log' ? 'active' : ''}`}
          onClick={() => setActiveTab('log')}
        >
          <Terminal size={14} style={{ marginRight: 5 }} />
          CLI Activity & Error Diagnostics Log
        </button>
      </div>

      {activeTab === 'config' ? (
        <div className="settings-content-body">
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
              Test Connection
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
                <span className="step-badge">Step 1: Authenticate Google Account (One-Time)</span>
                <button className="btn-copy-cmd" onClick={copyCmd1}>
                  {copiedCmd1 ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                  {copiedCmd1 ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <code>{authCmd}</code>
            </div>

            <div className="settings-cmd-box">
              <div className="cmd-box-header">
                <span className="step-badge">Step 2: Start REST API Server</span>
                <button className="btn-copy-cmd" onClick={copyCmd2}>
                  {copiedCmd2 ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                  {copiedCmd2 ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <code>{serverCmd}</code>
            </div>
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
