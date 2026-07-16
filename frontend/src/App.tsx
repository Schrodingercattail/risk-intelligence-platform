import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import RiskCommandCenter from './pages/RiskCommandCenter'
import Investigation from './pages/Investigation'
import DataPipeline from './pages/DataPipeline'
import ModelMonitoring from './pages/ModelMonitoring'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<RiskCommandCenter />} />
          <Route path="investigation" element={<Investigation />} />
          <Route path="pipeline" element={<DataPipeline />} />
          <Route path="model" element={<ModelMonitoring />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
