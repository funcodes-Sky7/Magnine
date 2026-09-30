import React, { useState } from 'react';
import TopBar from './TopBar';
import Sidebar from './Sidebar';

interface Props { children: React.ReactNode; }

function AppShell({ children }: Props) {
  const [studyArea] = useState('India Manganese Belt');
  const [modelVersion] = useState('v1.0');

  return (
    <div className="app-shell">
      <TopBar studyArea={studyArea} modelVersion={modelVersion} />
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

export default AppShell;
