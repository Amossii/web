import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import DataFilesPage from './pages/DataFilesPage'
import ModelsPage from './pages/ModelsPage'
import ClientsPage from './pages/ClientsPage'
import AgentChat from './components/AgentChat'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/datafiles" replace />} />
          <Route path="datafiles" element={<DataFilesPage />} />
          <Route path="models" element={<ModelsPage />} />
          <Route path="clients" element={<ClientsPage />} />
        </Route>
      </Routes>
      
      {/* 全局悬浮AI助手 */}
      <AgentChat />
    </>
  )
}

export default App

