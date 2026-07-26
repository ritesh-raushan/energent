import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Loader2, TrendingDown, TrendingUp, Zap } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'

const API_BASE = '/api'

export default function ClosedLoop() {
  const navigate = useNavigate()
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/loop/run`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Loop failed')
      }
      const data = await res.json()
      setResult(data)
      sessionStorage.setItem('lastLoop', JSON.stringify(data))
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const comparisonData = result ? [
    { name: 'Heating', baseline: result.baseline.summary.heating_kwh, optimized: result.optimized.summary.heating_kwh },
    { name: 'Cooling', baseline: result.baseline.summary.cooling_kwh, optimized: result.optimized.summary.cooling_kwh },
    { name: 'Fans', baseline: result.baseline.summary.fans_kwh, optimized: result.optimized.summary.fans_kwh },
    { name: 'Lighting', baseline: result.baseline.summary.lighting_kwh, optimized: result.optimized.summary.lighting_kwh },
    { name: 'Equipment', baseline: result.baseline.summary.equipment_kwh, optimized: result.optimized.summary.equipment_kwh },
  ] : []

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white">Closed-Loop Optimization</h1>
            <p className="text-gray-400 mt-1">AI-driven EnergyPlus setpoint optimization</p>
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center gap-2"
        >
          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {running ? 'Running Loop...' : 'Run Closed-Loop'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">{error}</div>
      )}

      {running && (
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8 text-center">
          <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Running Closed-Loop Optimization</h2>
          <p className="text-gray-400 text-sm">This runs two EnergyPlus simulations and may take several minutes...</p>
          <div className="mt-4 space-y-2 text-sm text-gray-500">
            <p>1. Running baseline simulation</p>
            <p>2. Analyzing energy data</p>
            <p>3. Generating ECMs with AI</p>
            <p>4. Modifying IDF setpoints</p>
            <p>5. Running optimized simulation</p>
            <p>6. Comparing results</p>
          </div>
        </div>
      )}

      {result && (
        <>
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingDown className="w-8 h-8 text-emerald-400" />
              <div>
                <h2 className="text-2xl font-bold text-white">{result.savings.percent}% Energy Savings</h2>
                <p className="text-emerald-400">{result.savings.baseline_kwh} kWh → {result.savings.optimized_kwh} kWh ({result.savings.kwh} kWh saved)</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Setpoint Changes</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-800 rounded-xl p-4">
                <span className="text-gray-400 text-sm">Heating Setpoint</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-white text-lg">{result.ecm.heating_occupied_c}°C</span>
                </div>
              </div>
              <div className="bg-gray-800 rounded-xl p-4">
                <span className="text-gray-400 text-sm">Cooling Setpoint</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-white text-lg">{result.ecm.cooling_occupied_c}°C</span>
                </div>
              </div>
            </div>
            <p className="text-gray-400 text-sm mt-4">{result.ecm.reasoning}</p>
          </div>

          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Baseline vs Optimized</h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                  formatter={(value) => `${value} kWh`}
                />
                <Legend />
                <Bar dataKey="baseline" name="Baseline" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="optimized" name="Optimized" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Baseline</h3>
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-gray-400">Total Electricity</span><span className="text-white font-semibold">{result.baseline.summary.total_electricity_kwh} kWh</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Heating</span><span className="text-white">{result.baseline.summary.heating_kwh} kWh ({result.baseline.summary.heating_pct}%)</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Cooling</span><span className="text-white">{result.baseline.summary.cooling_kwh} kWh ({result.baseline.summary.cooling_pct}%)</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Score</span><span className="text-white">{result.baseline.score}/100</span></div>
              </div>
            </div>
            <div className="bg-gray-900 rounded-2xl border border-emerald-500/30 p-6">
              <h3 className="text-lg font-semibold text-emerald-400 mb-4">Optimized</h3>
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-gray-400">Total Electricity</span><span className="text-emerald-400 font-semibold">{result.optimized.summary.total_electricity_kwh} kWh</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Heating</span><span className="text-emerald-400">{result.optimized.summary.heating_kwh} kWh ({result.optimized.summary.heating_pct}%)</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Cooling</span><span className="text-emerald-400">{result.optimized.summary.cooling_kwh} kWh ({result.optimized.summary.cooling_pct}%)</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Score</span><span className="text-emerald-400">{result.optimized.score}/100</span></div>
              </div>
            </div>
          </div>
        </>
      )}

      {!result && !running && (
        <div className="text-center py-20 text-gray-500">
          <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">Run the closed-loop optimization</p>
          <p className="text-sm mt-1">This will run baseline → analyze → modify IDF → re-run → compare</p>
        </div>
      )}
    </div>
  )
}
