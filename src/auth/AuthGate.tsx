import React from 'react';
import { useAuth } from './AuthContext';
import { LoginPage } from './LoginPage';

export const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading NotebookLM-py...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
};
