import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend } from 'recharts'
import { ArrowLeft, Bot, Loader2 } from 'lucide-react'
import RecommendationCard from '../components/RecommendationCard'
import { refineRecommendations } from '../api'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

export default function Results() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [refined, setRefined] = useState(null)
  const [refining, setRefining] = useState(false)
  const [refineError, setRefineError] = useState(null)

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('lastSimulation')
      if (stored) {
        setData(JSON.parse(stored))
      }
    } catch (e) {
      sessionStorage.removeItem('lastSimulation')
    }
  }, [])

  if (!data) {
    return (
      <div className="text-center py-20 text-gray-500">
        <p className="text-lg">No simulation results available</p>
        <button
          onClick={() => navigate('/simulation')}
          className="mt-4 text-emerald-400 hover:text-emerald-300"
        >
          Run a simulation first
        </button>
      </div>
    )
  }

  const { summary, analysis } = data

  const breakdownData = [
    { name: 'Heating', value: analysis.energy_breakdown.heating_kwh },
    { name: 'Cooling', value: analysis.energy_breakdown.cooling_kwh },
    { name: 'Fans', value: analysis.energy_breakdown.fans_kwh },
    { name: 'Lighting', value: analysis.energy_breakdown.lighting_kwh },
    { name: 'Equipment', value: analysis.energy_breakdown.equipment_kwh },
  ].filter(d => d.value > 0)

  const peakData = [
    { name: 'Heating', value: analysis.peak_load.peak_heating_pct },
    { name: 'Cooling', value: analysis.peak_load.peak_cooling_pct },
    { name: 'Fans', value: analysis.peak_load.peak_fans_pct },
    { name: 'Lighting', value: analysis.peak_load.peak_lighting_pct },
    { name: 'Equipment', value: analysis.peak_load.peak_equipment_pct },
  ].filter(d => d.value > 0)

  const handleRefine = async () => {
    setRefining(true)
    setRefineError(null)
    try {
      const result = await refineRecommendations(analysis)
      setRefined(result.result)
    } catch (err) {
      setRefineError(err.message)
    } finally {
      setRefining(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white">Results</h1>
            <p className="text-gray-400 mt-1">Simulation analysis and recommendations</p>
          </div>
        </div>
        <button
          onClick={handleRefine}
          disabled={refining}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2"
        >
          {refining ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
          {refining ? 'Refining...' : 'AI Refine'}
        </button>
      </div>

      {refineError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {refineError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Energy Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={breakdownData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {breakdownData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value} kWh`} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Peak Load Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={peakData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                formatter={(value) => `${value}%`}
              />
              <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Performance Summary</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-white">{summary.total_electricity_kwh}</p>
            <p className="text-gray-400 text-sm mt-1">Total kWh</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-white">{analysis.peak_load.peak_kw}</p>
            <p className="text-gray-400 text-sm mt-1">Peak kW</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-white">{analysis.hvac_summary.avg_zone_temp_c}°C</p>
            <p className="text-gray-400 text-sm mt-1">Avg Temp</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-emerald-400">{analysis.overall_score}</p>
            <p className="text-gray-400 text-sm mt-1">Score</p>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Thermal Comfort (Fanger PMV/PPD)</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className={`text-3xl font-bold ${Math.abs(analysis.thermal_comfort.pmv) <= 0.5 ? 'text-emerald-400' : Math.abs(analysis.thermal_comfort.pmv) <= 1.0 ? 'text-yellow-400' : 'text-red-400'}`}>
              {analysis.thermal_comfort.pmv}
            </p>
            <p className="text-gray-400 text-sm mt-1">PMV</p>
            <p className="text-gray-500 text-xs mt-1">-3 cold → +3 hot</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className={`text-3xl font-bold ${analysis.thermal_comfort.ppd <= 10 ? 'text-emerald-400' : analysis.thermal_comfort.ppd <= 20 ? 'text-yellow-400' : 'text-red-400'}`}>
              {analysis.thermal_comfort.ppd}%
            </p>
            <p className="text-gray-400 text-sm mt-1">PPD</p>
            <p className="text-gray-500 text-xs mt-1">target {'<'} 10%</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-blue-400 capitalize">{analysis.thermal_comfort.comfort_status}</p>
            <p className="text-gray-400 text-sm mt-1">Status</p>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold text-white">{analysis.thermal_comfort.air_temperature_c}°C</p>
            <p className="text-gray-400 text-sm mt-1">Air Temp</p>
            <p className="text-gray-500 text-xs mt-1">MRT: {analysis.thermal_comfort.mean_radiant_temperature_c}°C</p>
          </div>
        </div>
      </div>

      {refined ? (
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">AI-Refined Recommendations</h2>
          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 mb-4">
            <p className="text-gray-300">{refined.summary}</p>
          </div>
          {refined.additional_insights.length > 0 && (
            <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-4 mb-4">
              <h4 className="text-purple-400 font-medium mb-2">Additional Insights</h4>
              <ul className="space-y-1">
                {refined.additional_insights.map((insight, i) => (
                  <li key={i} className="text-sm text-gray-400">• {insight}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {refined.refined_recommendations.map((rec, i) => (
              <RecommendationCard key={i} recommendation={rec} />
            ))}
          </div>
        </div>
      ) : (
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">Rule-Based Recommendations</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analysis.recommendations.map((rec, i) => (
              <RecommendationCard key={i} recommendation={rec} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
