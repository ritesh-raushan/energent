import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Loader2, CheckCircle, XCircle, BarChart2, Thermometer, Zap, Fan, Activity } from 'lucide-react'
import { runSimulation } from '../api'

const API_BASE = '/api'

export default function Simulation() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('standard')
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [liveMetrics, setLiveMetrics] = useState([])
  const [currentMetrics, setCurrentMetrics] = useState(null)
  const eventSourceRef = useRef(null)
  const runIdRef = useRef(null)

  const handleRun = async () => {
    setStatus('running')
    setError(null)
    setLiveMetrics([])
    setCurrentMetrics(null)

    if (mode === 'stream') {
      await startStreamingSimulation()
    } else {
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
  }

  const startStreamingSimulation = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/start-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ output_dir: '/mnt/c/EnergentOutput' }),
      })
      if (!res.ok) throw new Error('Failed to start stream')
      const data = await res.json()
      runIdRef.current = data.run_id

      const eventSource = new EventSource(`${API_BASE}/simulation/stream/${data.run_id}`)
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const metrics = JSON.parse(event.data)
          setCurrentMetrics(metrics)
          setLiveMetrics(prev => [...prev.slice(-99), metrics])
        } catch (e) {
          console.error('Parse error:', e)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setStatus('success')
      }

      await runSimulation()
      setResult({ summary: { total_electricity_kwh: liveMetrics[liveMetrics.length - 1]?.electricity_kw || 0 } })
      sessionStorage.setItem('lastSimulation', JSON.stringify(result))
    } catch (err) {
      setError(err.message)
      setStatus('error')
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }

  const stopStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (runIdRef.current) {
      fetch(`${API_BASE}/simulation/stop-stream/${runIdRef.current}`, { method: 'POST' })
    }
    setStatus('idle')
  }

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, [])

  const statusConfig = {
    idle: { icon: Play, color: 'text-gray-400', bg: 'bg-gray-800', label: 'Ready' },
    running: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: mode === 'stream' ? 'Streaming Live Metrics...' : 'Running Simulation...' },
    success: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Complete' },
    error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Failed' },
  }

  const { icon: StatusIcon, color, bg, label } = statusConfig[status]

  const getComfortColor = (pmv) => {
    if (pmv === null || pmv === undefined) return 'text-gray-400'
    const abs = Math.abs(pmv)
    if (abs <= 0.5) return 'text-emerald-400'
    if (abs <= 1.0) return 'text-yellow-400'
    if (abs <= 2.0) return 'text-orange-400'
    return 'text-red-400'
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Simulation</h1>
          <p className="text-gray-400 mt-1">Run EnergyPlus building energy simulation</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setMode('standard')}
            disabled={status === 'running'}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'standard' ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Standard
          </button>
          <button
            onClick={() => setMode('stream')}
            disabled={status === 'running'}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'stream' ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Live Stream
          </button>
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8">
        <div className="text-center space-y-6">
          <div className={`w-20 h-20 rounded-full ${bg} flex items-center justify-center mx-auto`}>
            <StatusIcon className={`w-10 h-10 ${color} ${status === 'running' ? 'animate-spin' : ''}`} />
          </div>

          <div>
            <h2 className="text-xl font-semibold text-white">{label}</h2>
            <p className="text-gray-400 text-sm mt-1">
              {status === 'idle' && 'Choose mode and click to start'}
              {status === 'running' && mode === 'stream' && 'Receiving real-time EnergyPlus metrics...'}
              {status === 'running' && mode === 'standard' && 'Running EnergyPlus simulation... This may take a few minutes.'}
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

          {status === 'running' && mode === 'stream' && currentMetrics && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Thermometer className="w-4 h-4" />
                  <span>Zone Temp</span>
                </div>
                <div className="text-2xl font-bold text-white mt-1">{currentMetrics.zone_temp_c?.toFixed(1)}°C</div>
              </div>
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Zap className="w-4 h-4" />
                  <span>Power</span>
                </div>
                <div className="text-2xl font-bold text-white mt-1">{currentMetrics.electricity_kw?.toFixed(1)} kW</div>
              </div>
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Fan className="w-4 h-4" />
                  <span>Heating</span>
                </div>
                <div className="text-2xl font-bold text-red-400 mt-1">{currentMetrics.heating_kw?.toFixed(1)} kW</div>
              </div>
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Activity className="w-4 h-4" />
                  <span>Cooling</span>
                </div>
                <div className="text-2xl font-bold text-blue-400 mt-1">{currentMetrics.cooling_kw?.toFixed(1)} kW</div>
              </div>
            </div>
          )}

          {status === 'running' && mode === 'stream' && currentMetrics?.thermal_comfort && (
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 max-w-md mx-auto">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">PMV</span>
                <span className={`font-semibold ${getComfortColor(currentMetrics.thermal_comfort.pmv)}`}>
                  {currentMetrics.thermal_comfort.pmv.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm mt-1">
                <span className="text-gray-400">PPD</span>
                <span className="font-semibold text-white">{currentMetrics.thermal_comfort.ppd.toFixed(1)}%</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-1">
                <span className="text-gray-400">Status</span>
                <span className={`font-semibold capitalize ${getComfortColor(currentMetrics.thermal_comfort.pmv)}`}>
                  {currentMetrics.thermal_comfort.comfort_status}
                </span>
              </div>
            </div>
          )}

          {status === 'running' && (
            <div className="w-full max-w-md mx-auto">
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full animate-pulse w-2/3" />
              </div>
              <p className="text-gray-500 text-xs mt-2 text-center">
                {mode === 'stream' ? `Samples received: ${liveMetrics.length}` : 'This may take a few minutes...'}
              </p>
            </div>
          )}

          {status === 'running' && mode === 'standard' && (
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
                  <p className="text-white font-semibold">{result?.summary?.total_electricity_kwh || liveMetrics[liveMetrics.length - 1]?.electricity_kw || 0} kWh</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <span className="text-gray-400">Samples</span>
                  <p className="text-white font-semibold">{liveMetrics.length}</p>
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

          {(status === 'success' || status === 'error') && (
            <button
              onClick={handleRun}
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Run again
            </button>
          )}

          {status === 'running' && mode === 'stream' && (
            <button
              onClick={stopStream}
              className="text-red-400 hover:text-red-300 text-sm transition-colors"
            >
              Stop Stream
            </button>
          )}
        </div>
      </div>

      {mode === 'stream' && liveMetrics.length > 0 && (
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart2 className="w-5 h-5" />
            Live Power Consumption
          </h3>
          <div className="h-48 relative">
            <svg className="w-full h-full" viewBox="0 0 800 200">
              {liveMetrics.slice(-100).map((m, i) => {
                const x = (i / 99) * 800
                const y = 200 - Math.min(m.electricity_kw / 50, 1) * 180
                return (
                  <circle key={i} cx={x} cy={y} r={3} fill="#10b981" />
                )
              })}
              {liveMetrics.slice(-100).length > 1 && (
                <polyline
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2"
                  points={liveMetrics.slice(-100).map((m, i) => {
                    const x = (i / 99) * 800
                    const y = 200 - Math.min(m.electricity_kw / 50, 1) * 180
                    return `${x},${y}`
                  }).join(' ')}
                />
              )}
            </svg>
          </div>
          <p className="text-gray-400 text-sm text-center mt-2">
            Last {liveMetrics.length} samples • Latest: {liveMetrics[liveMetrics.length - 1]?.electricity_kw?.toFixed(1) || 0} kW
          </p>
        </div>
      )}

      {mode === 'stream' && liveMetrics.length > 0 && currentMetrics?.thermal_comfort && (
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Thermometer className="w-5 h-5" />
            Thermal Comfort Trend (PMV)
          </h3>
          <div className="h-48 relative">
            <svg className="w-full h-full" viewBox="0 0 800 200">
              <line x1="0" y1="100" x2="800" y2="100" stroke="#374151" strokeWidth="1" strokeDasharray="5,5" />
              <line x1="0" y1="85" x2="800" y2="85" stroke="#10b981" strokeWidth="1" strokeDasharray="2,2" />
              <line x1="0" y1="115" x2="800" y2="115" stroke="#10b981" strokeWidth="1" strokeDasharray="2,2" />
              {liveMetrics.slice(-100).filter(m => m.thermal_comfort).map((m, i) => {
                const x = (i / 99) * 800
                const y = 100 - (m.thermal_comfort.pmv / 3) * 80
                return <circle key={i} cx={x} cy={y} r={3} fill="#f59e0b" />
              })}
            </svg>
          </div>
          <p className="text-gray-400 text-sm text-center mt-2">
            Green zone: PMV -0.5 to +0.5 (Comfortable)
          </p>
        </div>
      )}

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