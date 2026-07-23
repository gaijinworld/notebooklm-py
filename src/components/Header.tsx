import React from 'react';
import { useAuth } from '../auth/AuthContext';
import { Settings, LogOut } from 'lucide-react';

interface HeaderProps {
  onToggleSettings: () => void;
  showSettings: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSettings }) => {
  const { user, signOutUser } = useAuth();
  const email = user?.email || user?.displayName || 'user@gaijinworld.com';
  const initial = (email[0] || 'U').toUpperCase();

  return (
    <header className="app-header">
      <h1 className="app-title">NotebookLM-py</h1>
      <div className="header-actions">
        <div className="user-profile-pill">
          <div className="user-avatar">{initial}</div>
          <span className="user-email-text">{email}</span>
        </div>
        <span className="version-live-badge">v2026.07.23.21 Live</span>
        <button className="btn-header-action" onClick={onToggleSettings} title="Settings">
          <Settings size={16} />
          <span>Settings</span>
        </button>
        <button className="btn-header-action btn-signout" onClick={signOutUser} title="Sign Out">
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  );
};
