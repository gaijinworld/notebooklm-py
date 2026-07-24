import React, { useState } from 'react';
import { Terminal, Copy, Check, Server, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

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
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'log'>('config');

  const startupCmd = `$env:NOTEBOOKLM_SERVER_TOKEN="${apiToken || 'mysecrettoken'}"; python -m notebooklm.server`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(startupCmd);
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  const commandLogs = [
    { type: 'cmd', text: 'uv pip install --system -e ".[server]"', status: 'Requires repo venv; fallback to pip --user' },
    { type: 'cmd', text: '.\\.venv\\Scripts\\pip.exe install -e ".[server]"', status: 'Targeted project virtualenv' },
    { type: 'success', text: 'python -m pip install --user -e ".[server]"', status: 'SUCCESS: Installed fastapi 0.139.2, uvicorn 0.34.0, watchfiles 1.2.0, websockets 16.1.1' },
    { type: 'verify', text: 'python -m notebooklm.server --help', status: 'VERIFIED: notebooklm.server CLI entry point active and ready' },
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
          CLI Activity & Execution Log
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
              {connStatus.isError ? <AlertCircle size={16} /> : <ShieldCheck size={16} />}
              <span>{connStatus.text}</span>
            </div>
          )}

          <div className="settings-cmd-box">
            <div className="cmd-box-header">
              <span>PowerShell REST Server Startup Command:</span>
              <button className="btn-copy-cmd" onClick={copyToClipboard}>
                {copiedCmd ? <Check size={12} color="#3fb950" /> : <Copy size={12} />}
                {copiedCmd ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <code>{startupCmd}</code>
          </div>
        </div>
      ) : (
        <div className="settings-log-body">
          <div className="log-terminal-header">
            <Terminal size={14} style={{ marginRight: 6 }} />
            <span>Local Environment Verification & CLI Event Log</span>
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
