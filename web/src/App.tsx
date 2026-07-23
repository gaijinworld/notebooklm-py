import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider } from './auth/AuthContext';
import { AuthGate } from './auth/AuthGate';
import { Header } from './components/Header';
import { SettingsPanel } from './components/SettingsPanel';
import { NotebookList, Notebook } from './components/NotebookList';
import { TabBar, TabType } from './components/TabBar';
import { TabContent } from './components/TabContent';

export const MainWorkspace: React.FC = () => {
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(localStorage.getItem('nblm_apiUrl') || 'http://localhost:8000');
  const [apiToken, setApiToken] = useState(localStorage.getItem('nblm_apiToken') || '');
  const [connStatus, setConnStatus] = useState<{ text: string; isError: boolean } | null>(null);

  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(null);
  const [notebooksLoading, setNotebooksLoading] = useState(false);

  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const [tabData, setTabData] = useState<Record<string, any[]>>({});
  const [selectedItem, setSelectedItem] = useState<any | null>(null);
  const [tabLoading, setTabLoading] = useState(false);

  const apiCall = useCallback(async (method: string, path: string, body?: any) => {
    const url = apiUrl.replace(/\/+$/, '') + path;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (apiToken) {
      headers['Authorization'] = `Bearer ${apiToken}`;
    }

    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error ${res.status}: ${text || res.statusText}`);
    }

    return res.json();
  }, [apiUrl, apiToken]);

  const loadNotebooks = useCallback(async () => {
    setNotebooksLoading(true);
    setConnStatus(null);
    try {
      const data = await apiCall('GET', '/notebooks');
      const list = Array.isArray(data) ? data : data.notebooks || [];
      setNotebooks(list);
      setConnStatus({ text: `Connected (${list.length} notebooks found)`, isError: false });
    } catch (err: any) {
      setConnStatus({ text: err.message || 'Connection failed', isError: true });
    } finally {
      setNotebooksLoading(false);
    }
  }, [apiCall]);

  const loadTabData = useCallback(async (nbId: string, tab: TabType) => {
    setTabLoading(true);
    let path = '';
    if (tab === 'sources') path = `/notebooks/${nbId}/sources`;
    else if (tab === 'artifacts') path = `/notebooks/${nbId}/artifacts`;
    else if (tab === 'notes') path = `/notebooks/${nbId}/notes`;
    else if (tab === 'research') path = `/notebooks/${nbId}/research`;

    try {
      const data = await apiCall('GET', path);
      const items = Array.isArray(data)
        ? data
        : data[tab] || data.artifacts || data.sources || data.notes || data.research_runs || [];
      setTabData((prev) => ({ ...prev, [`${nbId}_${tab}`]: items }));
    } catch (err) {
      console.warn(`Failed to fetch ${tab}:`, err);
      setTabData((prev) => ({ ...prev, [`${nbId}_${tab}`]: [] }));
    } finally {
      setTabLoading(false);
    }
  }, [apiCall]);

  useEffect(() => {
    if (selectedNotebook) {
      loadTabData(selectedNotebook.id, activeTab);
    }
  }, [selectedNotebook, activeTab, loadTabData]);

  const handleGenerate = async (type: string) => {
    if (!selectedNotebook) return;
    try {
      await apiCall('POST', `/notebooks/${selectedNotebook.id}/artifacts`, { type });
      alert(`Generation of ${type} started!`);
      loadTabData(selectedNotebook.id, 'artifacts');
    } catch (err: any) {
      alert(`Generation failed: ${err.message}`);
    }
  };

  const currentTabItems = selectedNotebook
    ? tabData[`${selectedNotebook.id}_${activeTab}`] || []
    : [];

  return (
    <div className="main-workspace-app">
      <Header
        showSettings={showSettings}
        onToggleSettings={() => setShowSettings(!showSettings)}
      />

      {showSettings && (
        <SettingsPanel
          apiUrl={apiUrl}
          setApiUrl={setApiUrl}
          apiToken={apiToken}
          setApiToken={setApiToken}
          onTestConnection={loadNotebooks}
          connStatus={connStatus}
        />
      )}

      <div className="workspace-body">
        <NotebookList
          notebooks={notebooks}
          selectedNotebook={selectedNotebook}
          onSelectNotebook={(nb) => {
            setSelectedNotebook(nb);
            setSelectedItem(null);
          }}
          onRefresh={loadNotebooks}
          loading={notebooksLoading}
        />

        <div className="workspace-main-content">
          <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
          <TabContent
            activeTab={activeTab}
            selectedNotebook={selectedNotebook}
            items={currentTabItems}
            selectedItem={selectedItem}
            onSelectItem={setSelectedItem}
            loading={tabLoading}
            onGenerate={handleGenerate}
          />
        </div>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <AuthGate>
        <MainWorkspace />
      </AuthGate>
    </AuthProvider>
  );
}
