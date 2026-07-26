import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Loader2, TrendingDown, Zap, Brain, Terminal, CheckCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'

const API_BASE = '/api'

export default function ClosedLoop() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('loop')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [agentSteps, setAgentSteps] = useState([])
  const [currentStep, setCurrentStep] = useState(0)
  const [expandedSteps, setExpandedSteps] = useState(new Set())

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('lastLoop')
      if (stored) {
        setResult(JSON.parse(stored))
      }
    } catch (e) {
      sessionStorage.removeItem('lastLoop')
    }
  }, [])

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    setResult(null)
    setAgentSteps([])
    setCurrentStep(0)
    setExpandedSteps(new Set())

    const endpoint = mode === 'agent' ? '/agent/run' : '/loop/run'
    const payload = mode === 'agent' ? {
      objective: 'Run closed-loop building energy optimization',
      context: {
        idf_path: 'simulation/idf/RefBldgSmallOfficeNew2004_Chicago.idf',
        weather_path: 'simulation/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw',
        output_dir: '/mnt/c/EnergentOutput',
      },
    } : {}

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Request failed')
      }
      const data = await res.json()

      if (mode === 'agent') {
        setAgentSteps(data.steps || [])
        setResult({
          savings: data.final_result?.savings || data.steps?.[data.steps.length - 1]?.result || {},
          ecm: data.steps?.find(s => s.tool === 'generate_ecms')?.result || {},
          baseline: data.steps?.find(s => s.tool === 'analyze_results' && s.iteration === 1)?.result || {},
          optimized: data.steps?.find(s => s.tool === 'analyze_results' && s.iteration > 1)?.result || {},
        })
      } else {
        setResult(data)
      }
      sessionStorage.setItem('lastLoop', JSON.stringify(data))
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const comparisonData = (result?.baseline?.summary && result?.optimized?.summary) ? [
    { name: 'Heating', baseline: result.baseline.summary.heating_kwh, optimized: result.optimized.summary.heating_kwh },
    { name: 'Cooling', baseline: result.baseline.summary.cooling_kwh, optimized: result.optimized.summary.cooling_kwh },
    { name: 'Fans', baseline: result.baseline.summary.fans_kwh, optimized: result.optimized.summary.fans_kwh },
    { name: 'Lighting', baseline: result.baseline.summary.lighting_kwh, optimized: result.optimized.summary.lighting_kwh },
    { name: 'Equipment', baseline: result.baseline.summary.equipment_kwh, optimized: result.optimized.summary.equipment_kwh },
  ] : []

  const comfortData = (result?.baseline?.thermal_comfort && result?.optimized?.thermal_comfort) ? [
    { name: 'PMV', baseline: result.baseline.thermal_comfort.pmv, optimized: result.optimized.thermal_comfort.pmv },
    { name: 'PPD %', baseline: result.baseline.thermal_comfort.ppd, optimized: result.optimized.thermal_comfort.ppd },
  ] : []

  const toggleStep = (idx) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

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
        <div className="flex gap-2">
          <button
            onClick={() => setMode('loop')}
            disabled={running}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'loop' ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            <Zap className="w-4 h-4 inline mr-1" /> Loop
          </button>
          <button
            onClick={() => setMode('agent')}
            disabled={running}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'agent' ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            <Brain className="w-4 h-4 inline mr-1" /> Agent
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">{error}</div>
      )}

      {running && (
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8">
          <div className="flex items-center gap-4 mb-6">
            <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
            <div>
              <h2 className="text-xl font-semibold text-white">
                {mode === 'agent' ? 'Agent Running Closed-Loop Optimization' : 'Running Closed-Loop Optimization'}
              </h2>
              <p className="text-gray-400 text-sm">This runs EnergyPlus simulations and may take several minutes...</p>
            </div>
          </div>

          {mode === 'agent' && agentSteps.length > 0 && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {agentSteps.map((step, idx) => (
                <div key={idx} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        step.result?.success === false ? 'bg-red-500/30 text-red-400' :
                        step.result?.success === true ? 'bg-emerald-500/30 text-emerald-400' :
                        'bg-yellow-500/30 text-yellow-400'
                      }`}>
                        {step.result?.success === false ? <AlertCircle className="w-4 h-4" /> :
                        step.result?.success === true ? <CheckCircle className="w-4 h-4" /> :
                        <Loader2 className="w-4 h-4 animate-spin" />}
                      </span>
                      <div>
                        <p className="font-medium text-white">{step.tool}</p>
                        <p className="text-gray-500 text-sm">Iteration {step.iteration}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => toggleStep(idx)}
                      className="text-gray-400 hover:text-white"
                    >
                      {expandedSteps.has(idx) ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                  </div>

                  {expandedSteps.has(idx) && (
                    <div className="mt-3 space-y-2 text-sm">
                      <div className="bg-gray-900 rounded p-3">
                        <span className="text-gray-400">Arguments:</span>
                        <pre className="text-white mt-1 whitespace-pre-wrap">{JSON.stringify(step.arguments, null, 2)}</pre>
                      </div>
                      <div className="bg-gray-900 rounded p-3">
                        <span className="text-gray-400">Result:</span>
                        <pre className="text-white mt-1 whitespace-pre-wrap max-h-64 overflow-y-auto">
                          {JSON.stringify(step.result, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {mode === 'loop' && (
            <div className="mt-4 space-y-2 text-sm text-gray-500">
              <p>1. Running baseline simulation</p>
              <p>2. Analyzing energy data</p>
              <p>3. Generating ECMs with AI</p>
              <p>4. Modifying IDF setpoints</p>
              <p>5. Running optimized simulation</p>
              <p>6. Comparing results</p>
            </div>
          )}
        </div>
      )}

      {result && (
        <>
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingDown className="w-8 h-8 text-emerald-400" />
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {result.savings?.percent || result.savings?.energy_savings_pct || 'N/A'}% Energy Savings
                </h2>
                <p className="text-emerald-400">
                  {result.savings?.baseline_kwh || result.savings?.baseline_kwh} kWh →
                  {result.savings?.optimized_kwh || result.savings?.optimized_kwh} kWh
                  ({result.savings?.kwh || result.savings?.energy_savings_kwh || 'N/A'} kWh saved)
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Setpoint Changes</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-800 rounded-xl p-4">
                <span className="text-gray-400 text-sm">Heating Setpoint</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-white text-lg">{result.ecm?.heating_occupied_c || result.ecm?.heating_setpoint_c || 'N/A'}°C</span>
                </div>
              </div>
              <div className="bg-gray-800 rounded-xl p-4">
                <span className="text-gray-400 text-sm">Cooling Setpoint</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-white text-lg">{result.ecm?.cooling_occupied_c || result.ecm?.cooling_setpoint_c || 'N/A'}°C</span>
                </div>
              </div>
            </div>
            <p className="text-gray-400 text-sm mt-4">{result.ecm?.reasoning || 'Agent-generated optimization'}</p>
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

          {comfortData.length > 0 && (
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Thermal Comfort Comparison</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={comfortData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                  />
                  <Legend />
                  <Bar dataKey="baseline" name="Baseline" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="optimized" name="Optimized" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Baseline</h3>
              <div className="space-y-3">
                {result.baseline?.summary && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-400">Total Electricity</span><span className="text-white font-semibold">{result.baseline.summary.total_electricity_kwh} kWh</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Heating</span><span className="text-white">{result.baseline.summary.heating_kwh} kWh ({result.baseline.summary.heating_pct}%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Cooling</span><span className="text-white">{result.baseline.summary.cooling_kwh} kWh ({result.baseline.summary.cooling_pct}%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Score</span><span className="text-white">{result.baseline.score || result.baseline.overall_score || 'N/A'}/100</span></div>
                  </>
                )}
                {result.baseline?.thermal_comfort && (
                  <>
                    <hr className="border-gray-700 my-3" />
                    <div className="flex justify-between"><span className="text-gray-400">PMV</span><span className="text-white font-semibold">{result.baseline.thermal_comfort.pmv}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">PPD</span><span className="text-white">{result.baseline.thermal_comfort.ppd}%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Status</span><span className="text-white capitalize">{result.baseline.thermal_comfort.comfort_status}</span></div>
                  </>
                )}
              </div>
            </div>
            <div className="bg-gray-900 rounded-2xl border border-emerald-500/30 p-6">
              <h3 className="text-lg font-semibold text-emerald-400 mb-4">Optimized</h3>
              <div className="space-y-3">
                {result.optimized?.summary && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-400">Total Electricity</span><span className="text-emerald-400 font-semibold">{result.optimized.summary.total_electricity_kwh} kWh</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Heating</span><span className="text-emerald-400">{result.optimized.summary.heating_kwh} kWh ({result.optimized.summary.heating_pct}%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Cooling</span><span className="text-emerald-400">{result.optimized.summary.cooling_kwh} kWh ({result.optimized.summary.cooling_pct}%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Score</span><span className="text-emerald-400">{result.optimized.score || result.optimized.overall_score || 'N/A'}/100</span></div>
                  </>
                )}
                {result.optimized?.thermal_comfort && (
                  <>
                    <hr className="border-gray-700 my-3" />
                    <div className="flex justify-between"><span className="text-gray-400">PMV</span><span className="text-emerald-400 font-semibold">{result.optimized.thermal_comfort.pmv}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">PPD</span><span className="text-emerald-400">{result.optimized.thermal_comfort.ppd}%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Status</span><span className="text-emerald-400 capitalize">{result.optimized.thermal_comfort.comfort_status}</span></div>
                  </>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {!result && !running && (
        <div className="text-center py-20 text-gray-500">
          <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">Run the closed-loop optimization</p>
          <p className="text-sm mt-1">Choose Loop (fixed pipeline) or Agent (autonomous tool-calling)</p>
        </div>
      )}
    </div>
  )
}