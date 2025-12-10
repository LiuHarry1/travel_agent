import { useState, lazy, Suspense } from 'react'
import './App.css'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'

// Lazy load pages for code splitting
const ChatPage = lazy(() => import('./components/ChatPage').then(module => ({ default: module.ChatPage })))
const AdminPage = lazy(() => import('./components/AdminPage').then(module => ({ default: module.AdminPage })))

type TabKey = 'chat' | 'admin'

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('chat')
  const [sidebarVisible, setSidebarVisible] = useState(true)

  const handleTabChange = (tab: TabKey) => {
    // Toggle behavior: if clicking the same tab, switch back to chat
    if (tab === 'admin' && activeTab === 'admin') {
      setActiveTab('chat')
    } else {
      setActiveTab(tab)
    }
  }

  const handleSidebarToggle = () => {
    setSidebarVisible((prev) => !prev)
  }

  return (
    <ErrorBoundary>
      <Layout
        sidebarVisible={sidebarVisible}
        activeTab={activeTab}
        onSidebarToggle={handleSidebarToggle}
        onTabChange={handleTabChange}
      >
        <Suspense fallback={
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <span style={{ marginLeft: '0.75rem' }}>Loading...</span>
          </div>
        }>
          {activeTab === 'chat' && <ChatPage />}
          {activeTab === 'admin' && <AdminPage />}
        </Suspense>
      </Layout>
    </ErrorBoundary>
  )
}

export default App
