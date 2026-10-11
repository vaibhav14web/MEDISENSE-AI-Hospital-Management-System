import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import LoginModal from './components/LoginModal';

import AnalyticsView from './views/AnalyticsView';
import AppointmentsView from './views/AppointmentsView';
import PatientsView from './views/PatientsView';
import DoctorsView from './views/DoctorsView';
import DepartmentsView from './views/DepartmentsView';
import BaselineView from './views/BaselineView';
import MLNoShowView from './views/MLNoShowView';
import ChatView from './views/ChatView';

function MainApp() {
  const { user, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState('chat');
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      setIsLoginModalOpen(true);
    }
  }, [loading, user]);

  const renderActiveView = () => {
    switch (currentTab) {
      case 'chat':
        return <ChatView />;
      case 'analytics':
        return <AnalyticsView />;
      case 'ml-no-show':
        return <MLNoShowView />;
      case 'appointments':
        return <AppointmentsView />;
      case 'patients':
        return <PatientsView />;
      case 'doctors':
        return <DoctorsView />;
      case 'departments':
        return <DepartmentsView />;
      case 'baseline':
        return <BaselineView />;
      default:
        return <ChatView />;
    }
  };

  return (
    <div className="app-layout">
      {/* Fixed Sidebar */}
      <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />

      {/* Main Content Area */}
      <div className="main-content">
        <Navbar
          currentTab={currentTab}
          onOpenLoginModal={() => setIsLoginModalOpen(true)}
        />
        <main>{renderActiveView()}</main>
      </div>

      {/* Authentication Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
