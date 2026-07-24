import React, { useState } from 'react';
import { TabType } from './TabBar';
import { Notebook } from './NotebookList';
import { Sparkles, CheckCircle, AlertCircle } from 'lucide-react';

interface TabContentProps {
  activeTab: TabType;
  selectedNotebook: Notebook | null;
  items: any[];
  selectedItem: any | null;
  onSelectItem: (item: any) => void;
  loading: boolean;
  onGenerate: (type: string) => void;
}

export const TabContent: React.FC<TabContentProps> = ({
  activeTab,
  selectedNotebook,
  items,
  selectedItem,
  onSelectItem,
  loading,
  onGenerate
}) => {
  const [generateType, setGenerateType] = useState('audio');

  const getStatusBadge = (status?: string) => {
    const s = status?.toLowerCase() || 'ready';
    if (s === 'ready' || s === 'completed') {
      return <span className="status-badge ready"><CheckCircle size={10} style={{marginRight:3}} />{s}</span>;
    }
    if (s === 'pending' || s === 'processing') {
      return <span className="status-badge pending">{s}</span>;
    }
    return <span className="status-badge failed"><AlertCircle size={10} style={{marginRight:3}} />{s}</span>;
  };

  return (
    <div className="pane-tabs-and-detail">
      <div className="pane-tabs">
        {selectedNotebook && activeTab === 'artifacts' && (
          <div className="generate-action-bar">
            <select
              value={generateType}
              onChange={(e) => setGenerateType(e.target.value)}
              className="generate-select"
            >
              <option value="audio">Audio Overview</option>
              <option value="video">Video</option>
              <option value="cinematic-video">Cinematic Video</option>
              <option value="slide-deck">Slide Deck</option>
              <option value="quiz">Quiz</option>
              <option value="flashcards">Flashcards</option>
              <option value="infographic">Infographic</option>
              <option value="data-table">Data Table</option>
              <option value="mind-map">Mind Map</option>
              <option value="report">Report</option>
            </select>
            <button className="btn-generate" onClick={() => onGenerate(generateType)}>
              <Sparkles size={14} style={{ marginRight: 4 }} />
              Generate
            </button>
          </div>
        )}

        <div className="tab-items-scroll">
          {!selectedNotebook ? (
            <div className="empty-state-card">
              <p>Select a notebook to browse its contents.</p>
            </div>
          ) : loading ? (
            <div className="loading-state-card">Loading {activeTab}...</div>
          ) : items.length === 0 ? (
            <div className="empty-state-card">
              <p>No {activeTab} found in this notebook.</p>
            </div>
          ) : (
            items.map((item) => {
              const id = item.id || item.source_id || item.artifact_id || item.note_id || item.run_id || '';
              const title = item.title || item.name || item.kind || item.type || 'Untitled';
              const isActive = selectedItem && (selectedItem.id === id || selectedItem.source_id === id);

              return (
                <div
                  key={id}
                  className={`list-item-card ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectItem(item)}
                >
                  <div className="li-title">{title}</div>
                  <div className="li-meta">
                    <span className="kind-tag">{item.kind || item.type || activeTab}</span>
                    {getStatusBadge(item.status || item.state)}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="pane-detail">
        {!selectedItem ? (
          <div className="detail-empty-welcome">
            <h2>NotebookLM-py Interactive Browser</h2>
            <p>
              This interface connects to the <code>notebooklm-server</code> REST API to browse your notebooks, sources, and generated artifacts.
            </p>
            <p className="sub-text">
              Click <strong>Settings</strong> in the top bar to configure the API URL and bearer token, then click <strong>Test Connection</strong>.
            </p>
            <p className="sub-text">If the server is not running, start it with:</p>
            <p className="code-block-p">
              <code>$env:NOTEBOOKLM_SERVER_TOKEN="mysecrettoken"; notebooklm-server</code>
            </p>
            <div className="welcome-links">
              <a href="https://github.com/gaijinworld/notebooklm-py" target="_blank" rel="noreferrer">
                GitHub Repo
              </a>
              <a href="https://github.com/gaijinworld/notebooklm-py/blob/main/README.md" target="_blank" rel="noreferrer">
                Docs
              </a>
              <a href="https://github.com/gaijinworld/notebooklm-py/blob/main/CHANGELOG.md" target="_blank" rel="noreferrer">
                Changelog
              </a>
            </div>
          </div>
        ) : (
          <div className="detail-content-view">
            <div className="detail-card-box">
              <h3>{selectedItem.title || selectedItem.name || 'Item Details'}</h3>
              <div className="field-row">
                <span className="field-label">ID:</span>
                <span className="field-val">{selectedItem.id || selectedItem.source_id || selectedItem.artifact_id}</span>
              </div>
              <div className="field-row">
                <span className="field-label">Type / Kind:</span>
                <span className="field-val">{selectedItem.kind || selectedItem.type || 'N/A'}</span>
              </div>
              <div className="field-row">
                <span className="field-label">Status:</span>
                <span className="field-val">{selectedItem.status || selectedItem.state || 'Ready'}</span>
              </div>
              {selectedItem.url && (
                <div className="field-row">
                  <span className="field-label">URL / File:</span>
                  <a className="field-link" href={selectedItem.url} target="_blank" rel="noreferrer">
                    {selectedItem.url}
                  </a>
                </div>
              )}
              {selectedItem.content || selectedItem.text ? (
                <div className="detail-text-block">
                  <pre>{selectedItem.content || selectedItem.text}</pre>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
