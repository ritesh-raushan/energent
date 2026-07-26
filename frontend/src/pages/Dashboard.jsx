import { useState, useEffect } from 'react'
import { Zap, Thermometer, Fan, Lightbulb, Flame, Activity, Heart } from 'lucide-react'
import EnergyCard from '../components/EnergyCard'
import RecommendationCard from '../components/RecommendationCard'
import { runSimulation } from '../api'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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

  const handleRunSimulation = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await runSimulation()
      setData(result)
      sessionStorage.setItem('lastSimulation', JSON.stringify(result))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">Building energy optimization overview</p>
        </div>
        <button
          onClick={handleRunSimulation}
          disabled={loading}
          className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center gap-2"
        >
          <Zap className="w-4 h-4" />
          {loading ? 'Running...' : 'Run Simulation'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <EnergyCard
              title="Total Electricity"
              value={data.summary.total_electricity_kwh}
              unit="kWh"
              icon={Zap}
              color="emerald"
            />
            <EnergyCard
              title="Peak Load"
              value={data.analysis.peak_load.peak_kw}
              unit="kW"
              icon={Activity}
              color="red"
            />
            <EnergyCard
              title="Avg Zone Temp"
              value={data.analysis.hvac_summary.avg_zone_temp_c}
              unit="°C"
              icon={Thermometer}
              color="blue"
            />
            <EnergyCard
              title="Score"
              value={data.analysis.overall_score}
              unit="/100"
              icon={Zap}
              color="purple"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <EnergyCard
              title="PMV"
              value={data.analysis.thermal_comfort.pmv}
              unit=""
              icon={Heart}
              color={Math.abs(data.analysis.thermal_comfort.pmv) <= 0.5 ? 'emerald' : Math.abs(data.analysis.thermal_comfort.pmv) <= 1.0 ? 'yellow' : 'red'}
            />
            <EnergyCard
              title="PPD"
              value={data.analysis.thermal_comfort.ppd}
              unit="%"
              icon={Heart}
              color={data.analysis.thermal_comfort.ppd <= 10 ? 'emerald' : data.analysis.thermal_comfort.ppd <= 20 ? 'yellow' : 'red'}
            />
            <EnergyCard
              title="Comfort"
              value={data.analysis.thermal_comfort.comfort_status}
              unit=""
              icon={Thermometer}
              color="blue"
            />
            <EnergyCard
              title="Air Velocity"
              value={data.analysis.thermal_comfort.air_velocity_ms}
              unit="m/s"
              icon={Fan}
              color="emerald"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <EnergyCard
              title="Heating"
              value={data.analysis.energy_breakdown.heating_kwh}
              unit="kWh"
              icon={Flame}
              color="orange"
            />
            <EnergyCard
              title="Cooling"
              value={data.analysis.energy_breakdown.cooling_kwh}
              unit="kWh"
              icon={Fan}
              color="blue"
            />
            <EnergyCard
              title="Fans"
              value={data.analysis.energy_breakdown.fans_kwh}
              unit="kWh"
              icon={Fan}
              color="emerald"
            />
            <EnergyCard
              title="Lighting"
              value={data.analysis.energy_breakdown.lighting_kwh}
              unit="kWh"
              icon={Lightbulb}
              color="yellow"
            />
            <EnergyCard
              title="Equipment"
              value={data.analysis.energy_breakdown.equipment_kwh}
              unit="kWh"
              icon={Zap}
              color="purple"
            />
          </div>

          {data.analysis.recommendations.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Recommendations</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.analysis.recommendations.map((rec, i) => (
                  <RecommendationCard key={i} recommendation={rec} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!data && !loading && (
        <div className="text-center py-20 text-gray-500">
          <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">Run a simulation to see results</p>
          <p className="text-sm mt-1">Click the button above to start</p>
        </div>
      )}
    </div>
  )
}
