const API_BASE = '/api'

function extractError(err) {
  if (typeof err.detail === 'string') return err.detail
  if (err.detail?.message) return err.detail.message
  return 'An error occurred'
}

export async function runSimulation() {
  const res = await fetch(`${API_BASE}/simulation/run`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(extractError(err))
  }
  return res.json()
}

export async function startSimulationStream(outputDir = '/mnt/c/EnergentOutput') {
  const res = await fetch(`${API_BASE}/simulation/start-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ output_dir: outputDir }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(extractError(err))
  }
  return res.json()
}

export function streamSimulationMetrics(runId, onMessage) {
  const eventSource = new EventSource(`${API_BASE}/simulation/stream/${runId}`)
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.warn('Failed to parse SSE data:', e)
    }
  }
  eventSource.onerror = () => {
    eventSource.close()
  }
  return () => eventSource.close()
}

export async function stopSimulationStream(runId) {
  const res = await fetch(`${API_BASE}/simulation/stop-stream/${runId}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(extractError(err))
  }
  return res.json()
}

export async function refineRecommendations(analysis) {
  const res = await fetch(`${API_BASE}/llm/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(extractError(err))
  }
  return res.json()
}

export async function askLLM(analysis, question) {
  const res = await fetch(`${API_BASE}/llm/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis, question }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(extractError(err))
  }
  return res.json()
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

export async function checkLLMHealth() {
  const res = await fetch(`${API_BASE}/llm/health`)
  return res.json()
}
