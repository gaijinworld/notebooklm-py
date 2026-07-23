import React from 'react';

export type TabType = 'sources' | 'artifacts' | 'notes' | 'research';

interface TabBarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export const TabBar: React.FC<TabBarProps> = ({ activeTab, onTabChange }) => {
  const tabs: { id: TabType; label: string }[] = [
    { id: 'sources', label: 'Sources' },
    { id: 'artifacts', label: 'Artifacts' },
    { id: 'notes', label: 'Notes' },
    { id: 'research', label: 'Research' },
  ];

  return (
    <div className="tab-bar-container">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};
