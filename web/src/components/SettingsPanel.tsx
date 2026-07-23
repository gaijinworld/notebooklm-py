import React from 'react';

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
  return (
    <div className="settings-panel-box">
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
        <label htmlFor="apiTokenInput">Bearer Token</label>
        <input
          id="apiTokenInput"
          type="password"
          placeholder="NOTEBOOKLM_SERVER_TOKEN"
          value={apiToken}
          onChange={(e) => {
            setApiToken(e.target.value);
            localStorage.setItem('nblm_apiToken', e.target.value);
          }}
        />
      </div>

      <button className="btn-test-conn" onClick={onTestConnection}>
        Test Connection
      </button>

      {connStatus && (
        <span className={`conn-status-msg ${connStatus.isError ? 'err' : 'ok'}`}>
          {connStatus.text}
        </span>
      )}
    </div>
  );
};
