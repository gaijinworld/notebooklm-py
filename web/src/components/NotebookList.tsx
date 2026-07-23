import React from 'react';
import { RefreshCw, BookOpen } from 'lucide-react';

export interface Notebook {
  id: string;
  title: string;
  source_count?: number;
  sources_count?: number;
  created_at?: string;
  updated_at?: string;
}

interface NotebookListProps {
  notebooks: Notebook[];
  selectedNotebook: Notebook | null;
  onSelectNotebook: (nb: Notebook) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const NotebookList: React.FC<NotebookListProps> = ({
  notebooks,
  selectedNotebook,
  onSelectNotebook,
  onRefresh,
  loading
}) => {
  return (
    <div className="pane-notebooks">
      <div className="pane-header">
        <span>Notebooks</span>
        <button className="btn-icon-text" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={12} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="notebook-scroll-list">
        {notebooks.length === 0 ? (
          <div className="empty-state-card">
            <p>Connect to the API to list notebooks.</p>
          </div>
        ) : (
          notebooks.map((nb) => {
            const isActive = selectedNotebook?.id === nb.id;
            const count = nb.source_count ?? nb.sources_count ?? 0;
            return (
              <div
                key={nb.id}
                className={`notebook-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectNotebook(nb)}
              >
                <div className="nb-title">
                  <BookOpen size={14} style={{ marginRight: 6 }} />
                  {nb.title || 'Untitled Notebook'}
                </div>
                <div className="nb-meta">
                  <span>{count} {count === 1 ? 'source' : 'sources'}</span>
                  <span>•</span>
                  <span>ID: {nb.id.slice(0, 8)}...</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
