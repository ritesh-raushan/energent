import { AlertTriangle, Lightbulb, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

const priorityColors = {
  high: 'border-red-500/30 bg-red-500/5',
  medium: 'border-yellow-500/30 bg-yellow-500/5',
  low: 'border-blue-500/30 bg-blue-500/5',
}

const priorityBadge = {
  high: 'bg-red-500/20 text-red-400',
  medium: 'bg-yellow-500/20 text-yellow-400',
  low: 'bg-blue-500/20 text-blue-400',
}

export default function RecommendationCard({ recommendation }) {
  const [expanded, setExpanded] = useState(false)
  const { category, priority, title, description, estimated_savings_kwh, estimated_savings_pct, action_items, refined_description, estimated_impact } = recommendation

  const desc = refined_description || description

  return (
    <div className={`rounded-xl border p-5 ${priorityColors[priority] || priorityColors.medium}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          <span className="text-sm font-medium text-gray-300">{category}</span>
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${priorityBadge[priority] || priorityBadge.medium}`}>
          {priority}
        </span>
      </div>
      <h3 className="text-white font-semibold mb-2">{title}</h3>
      <p className="text-gray-400 text-sm mb-3">{desc}</p>

      {(estimated_savings_kwh > 0 || estimated_impact) && (
        <div className="flex flex-wrap gap-3 mb-3">
          {estimated_savings_kwh > 0 && (
            <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full">
              Save ~{estimated_savings_kwh.toFixed(1)} kWh ({estimated_savings_pct}%)
            </span>
          )}
          {estimated_impact && (
            <span className="text-xs bg-purple-500/10 text-purple-400 px-2 py-1 rounded-full">
              {estimated_impact}
            </span>
          )}
        </div>
      )}

      {action_items && action_items.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Show'} action items
          </button>
          {expanded && (
            <ul className="mt-2 space-y-1">
              {action_items.map((item, i) => (
                <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
