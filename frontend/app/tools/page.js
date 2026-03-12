'use client'
import { useEffect, useState, useRef } from 'react'
import { Wrench, Activity, CheckCircle, XCircle, Clock, Play, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { apiGet, apiPost, backendUrl } from '@/lib/api'

const TOOL_GROUPS = [
  { label: 'SERP', color: 'text-accent', tools: ['search_serp','search_web','search_news','get_related_questions'] },
  { label: 'Keywords', color: 'text-accent4', tools: ['get_keyword_volume','get_keyword_difficulty','get_keyword_suggestions','get_competitor_keywords'] },
  { label: 'GSC', color: 'text-accent3', tools: ['gsc_get_rankings','gsc_get_top_queries','gsc_detect_ranking_drops'] },
  { label: 'GA4', color: 'text-purple-400', tools: ['ga4_get_page_traffic','ga4_get_top_pages','ga4_detect_traffic_drops'] },
  { label: 'Filesystem', color: 'text-orange-400', tools: ['write_stage_output','write_memory','append_log'] },
]

const STATUS_COLOR = { ok: 'text-accent3', error: 'text-accent5', pending: 'text-muted' }
const STATUS_DOT   = { ok: 'bg-accent3', error: 'bg-accent5', pending: 'bg-dim animate-pulse' }

function ToolCallRow({ call, expanded, onToggle }) {
  return (
    <div className="border-b border-border/50 last:border-0">
      <div className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface2/50 transition-colors cursor-pointer group"
           onClick={onToggle}>
        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[call.status]}`} />
        <span className={`text-xs font-mono ${STATUS_COLOR[call.status]}`}>{call.tool}</span>
        <span className="text-xs text-muted flex-1 truncate hidden sm:block">
          {Object.entries(call.args || {}).slice(0,2).map(([k,v]) => `${k}: ${String(v).slice(0,30)}`).join(' · ')}
        </span>
        <span className="text-xs text-muted ml-auto">{call.duration_ms}ms</span>
        <span className="text-xs text-dim">{new Date(call.timestamp).toLocaleTimeString()}</span>
        {expanded ? <ChevronUp size={10} className="text-dim" /> : <ChevronDown size={10} className="text-dim" />}
      </div>
      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-muted mb-1 uppercase tracking-widest">Args</div>
            <pre className="text-xs text-white bg-surface2 border border-border rounded p-2 overflow-auto max-h-32">
              {JSON.stringify(call.args, null, 2)}
            </pre>
          </div>
          <div>
            <div className="text-xs text-muted mb-1 uppercase tracking-widest">
              {call.error ? 'Error' : 'Result'}
            </div>
            <pre className={`text-xs bg-surface2 border rounded p-2 overflow-auto max-h-32 ${call.error ? 'text-accent5 border-accent5/30' : 'text-white border-border'}`}>
              {call.error || JSON.stringify(call.result, null, 2)?.slice(0, 500)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function ToolTester({ tools }) {
  const [selected, setSelected] = useState('')
  const [argsText, setArgsText] = useState('{}')
  const [result, setResult]     = useState(null)
  const [running, setRunning]   = useState(false)
  const [error, setError]       = useState(null)

  const runTool = async () => {
    if (!selected) return
    setRunning(true); setError(null); setResult(null)
    try {
      const args = JSON.parse(argsText)
      const data = await apiPost(`/tools/${selected}`, args)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="bg-surface border border-border rounded overflow-hidden">
      <div className="px-4 py-3 border-b border-border bg-surface2 flex items-center gap-2">
        <Wrench size={12} className="text-accent" />
        <span className="text-xs font-bold text-white tracking-wide">TOOL TESTER</span>
      </div>
      <div className="p-4 space-y-3">
        <div>
          <label className="block text-xs text-muted mb-1.5">Select Tool</label>
          <select value={selected} onChange={e => setSelected(e.target.value)}
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent">
            <option value="">— pick a tool —</option>
            {TOOL_GROUPS.map(g => (
              <optgroup key={g.label} label={g.label}>
                {g.tools.map(t => <option key={t} value={t}>{t}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted mb-1.5">Arguments (JSON)</label>
          <textarea value={argsText} onChange={e => setArgsText(e.target.value)} rows={4}
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-accent resize-none" />
        </div>
        <button onClick={runTool} disabled={!selected || running}
          className="w-full flex items-center justify-center gap-2 py-2 bg-accent/10 text-accent border border-accent/20 text-xs font-bold rounded hover:bg-accent/20 transition-colors disabled:opacity-50">
          {running ? <RefreshCw size={11} className="animate-spin" /> : <Play size={11} />}
          {running ? 'RUNNING...' : 'RUN TOOL'}
        </button>
        {error && (
          <div className="text-xs text-accent5 bg-accent5/10 border border-accent5/30 rounded px-3 py-2">{error}</div>
        )}
        {result && (
          <pre className="text-xs text-white bg-surface2 border border-border rounded p-3 overflow-auto max-h-48 font-mono">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

export default function ToolsPage() {
  const [calls, setCalls]       = useState([])
  const [tools, setTools]       = useState([])
  const [expanded, setExpanded] = useState(null)
  const [live, setLive]         = useState(true)
  const [filter, setFilter]     = useState('all')
  const intervalRef             = useRef(null)

  const fetchData = async () => {
    try {
      const [callsData, toolsData] = await Promise.all([
        apiGet('/tool-calls', { limit: 100 }),
        apiGet('/tools'),
      ])
      setCalls((callsData.calls || []).reverse())
      setTools(toolsData.tools || [])
    } catch { }
  }

  useEffect(() => {
    fetchData()
    if (live) {
      intervalRef.current = setInterval(fetchData, 2000)
    }
    return () => clearInterval(intervalRef.current)
  }, [live])

  const stats = {
    total:   calls.length,
    ok:      calls.filter(c => c.status === 'ok').length,
    errors:  calls.filter(c => c.status === 'error').length,
    avg_ms:  calls.length ? Math.round(calls.reduce((a,c) => a + (c.duration_ms||0), 0) / calls.length) : 0,
  }

  const filtered = filter === 'all' ? calls : calls.filter(c => c.status === filter || c.tool.includes(filter))

  return (
    <div className="animate-fade-in">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
            <Wrench size={10} className="text-accent" /> Tool Server
          </div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Tool Monitor</h1>
          <p className="text-muted text-xs mt-1">Live tool call feed · Test tools · Monitor errors</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setLive(l => !l)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs border rounded transition-colors
              ${live ? 'text-accent3 border-accent3/30 bg-accent3/10' : 'text-muted border-border'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${live ? 'bg-accent3 animate-pulse' : 'bg-dim'}`} />
            {live ? 'LIVE' : 'Paused'}
          </button>
          <button onClick={fetchData} className="px-3 py-2 text-xs text-muted border border-border rounded hover:text-white transition-colors">
            <RefreshCw size={11} />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Total Calls',  value: stats.total,   color: 'text-accent' },
          { label: 'Successful',   value: stats.ok,      color: 'text-accent3' },
          { label: 'Errors',       value: stats.errors,  color: 'text-accent5' },
          { label: 'Avg Duration', value: `${stats.avg_ms}ms`, color: 'text-accent4' },
        ].map(s => (
          <div key={s.label} className="bg-surface border border-border rounded p-4">
            <div className="text-xs text-muted mb-1">{s.label}</div>
            <div className={`text-2xl font-sans font-bold ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Live feed */}
        <div className="col-span-2">
          <div className="bg-surface border border-border rounded overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface2">
              <div className="flex items-center gap-2">
                <Activity size={12} className="text-accent" />
                <span className="text-xs font-bold text-white tracking-wide">LIVE TOOL CALLS</span>
                {live && <span className="text-xs text-accent3 animate-pulse">● LIVE</span>}
              </div>
              <div className="flex gap-1">
                {['all','ok','error'].map(f => (
                  <button key={f} onClick={() => setFilter(f)}
                    className={`px-2 py-1 text-xs rounded transition-colors capitalize
                      ${filter === f ? 'text-accent bg-accent/10 border border-accent/20' : 'text-muted hover:text-white border border-transparent'}`}>
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-[600px] overflow-auto">
              {filtered.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted">No tool calls yet. Run a pipeline to see activity.</div>
              ) : (
                filtered.map(call => (
                  <ToolCallRow key={call.id} call={call}
                    expanded={expanded === call.id}
                    onToggle={() => setExpanded(expanded === call.id ? null : call.id)} />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          <ToolTester tools={tools} />

          {/* Tool groups */}
          <div className="bg-surface border border-border rounded overflow-hidden">
            <div className="px-4 py-3 border-b border-border bg-surface2 text-xs font-bold text-white tracking-wide">
              AVAILABLE TOOLS
            </div>
            <div className="p-3 space-y-3">
              {TOOL_GROUPS.map(g => (
                <div key={g.label}>
                  <div className={`text-xs font-bold mb-1.5 ${g.color}`}>{g.label}</div>
                  <div className="space-y-1">
                    {g.tools.map(t => {
                      const recent = calls.find(c => c.tool === t)
                      return (
                        <div key={t} className="flex items-center gap-2 text-xs">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${recent ? (recent.status === 'ok' ? 'bg-accent3' : 'bg-accent5') : 'bg-dim'}`} />
                          <span className="text-muted font-mono truncate">{t}</span>
                          {recent && <span className="ml-auto text-dim">{recent.duration_ms}ms</span>}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
