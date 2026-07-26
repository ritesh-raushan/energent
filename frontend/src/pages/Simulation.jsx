import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { runSimulation } from '../api'

export default function Simulation() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    setStatus('running')
    setError(null)
    try {
      const data = await runSimulation()
      setResult(data)
      setStatus('success')
      sessionStorage.setItem('lastSimulation', JSON.stringify(data))
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  const statusConfig = {
    idle: { icon: Play, color: 'text-gray-400', bg: 'bg-gray-800', label: 'Ready' },
    running: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Running...' },
    success: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Complete' },
    error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Failed' },
  }

  const { icon: StatusIcon, color, bg, label } = statusConfig[status]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Simulation</h1>
        <p className="text-gray-400 mt-1">Run EnergyPlus building energy simulation</p>
      </div>

      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8">
        <div className="text-center space-y-6">
          <div className={`w-20 h-20 rounded-full ${bg} flex items-center justify-center mx-auto`}>
            <StatusIcon className={`w-10 h-10 ${color} ${status === 'running' ? 'animate-spin' : ''}`} />
          </div>

          <div>
            <h2 className="text-xl font-semibold text-white">{label}</h2>
            <p className="text-gray-400 text-sm mt-1">
              {status === 'idle' && 'Click to start the EnergyPlus simulation'}
              {status === 'running' && 'Running EnergyPlus simulation... This may take a few minutes.'}
              {status === 'success' && 'Simulation completed successfully!'}
              {status === 'error' && 'Simulation failed. Check the error below.'}
            </p>
          </div>

          {status === 'idle' && (
            <button
              onClick={handleRun}
              className="px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-xl transition-colors flex items-center gap-2 mx-auto"
            >
              <Play className="w-5 h-5" />
              Run Simulation
            </button>
          )}

          {status === 'running' && (
            <div className="w-full max-w-md mx-auto">
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full animate-pulse w-2/3" />
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 max-w-md mx-auto text-sm">
                <div className="bg-gray-800 rounded-lg p-3">
                  <span className="text-gray-400">Total Energy</span>
                  <p className="text-white font-semibold">{result.summary.total_electricity_kwh} kWh</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <span className="text-gray-400">Records</span>
                  <p className="text-white font-semibold">{result.record_count}</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/results')}
                className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-xl transition-colors"
              >
                View Results
              </button>
            </div>
          )}

          {status === 'error' && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm max-w-md mx-auto">
              {error}
            </div>
          )}

          {status !== 'idle' && status !== 'running' && (
            <button
              onClick={handleRun}
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Run again
            </button>
          )}
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Configuration</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Building Model</span>
            <p className="text-white mt-1">RefBldgSmallOfficeNew2004_Chicago.idf</p>
          </div>
          <div>
            <span className="text-gray-400">Weather File</span>
            <p className="text-white mt-1">USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw</p>
          </div>
          <div>
            <span className="text-gray-400">Location</span>
            <p className="text-white mt-1">Chicago, Illinois</p>
          </div>
          <div>
            <span className="text-gray-400">Simulation Period</span>
            <p className="text-white mt-1">Full Year (8760 hours)</p>
          </div>
        </div>
      </div>
    </div>
  )
}
