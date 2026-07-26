import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Simulation from './pages/Simulation'
import Results from './pages/Results'
import ClosedLoop from './pages/ClosedLoop'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="simulation" element={<Simulation />} />
            <Route path="results" element={<Results />} />
            <Route path="closed-loop" element={<ClosedLoop />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
