'use client'
import { useEffect, useState, useRef } from 'react'
import { Wrench, Activity, RefreshCw, Play, ChevronDown, ChevronUp } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const TOOL_GROUPS = [
  { label: 'SERP',       color: '#0041FF', tools: ['search_serp','search_web','search_news','get_related_questions'] },
  { label: 'Keywords',   color: '#D97706', tools: ['get_keyword_volume','get_keyword_difficulty','get_keyword_suggestions','get_competitor_keywords'] },
  { label: 'GSC',        color: '#059669', tools: ['gsc_get_rankings','gsc_get_top_queries','gsc_detect_ranking_drops'] },
  { label: 'GA4',        color: '#7C3AED', tools: ['ga4_get_page_traffic','ga4_get_top_pages','ga4_detect_traffic_drops'] },
  { label: 'Filesystem', color: '#DC2626', tools: ['write_stage_output','write_memory','append_log'] },
]

function ToolCallRow({ call, expanded, onToggle }) {
  const sc = call.status === 'ok' ? '#059669' : '#DC2626'
  const sb = call.status === 'ok' ? '#ECFDF5' : '#FEF2F2'
  return (
    <div style={{ borderBottom: '1px solid #E5E5E0' }}>
      <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', cursor: 'pointer', transition: 'background 0.1s' }}
        onMouseEnter={e => e.currentTarget.style.background = '#FAFAF8'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: sc, flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: '#0A0A0A', fontWeight: 500, minWidth: 180 }}>{call.tool}</span>
        <span style={{ fontSize: 11, color: '#8A8A82', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {Object.entries(call.args || {}).slice(0,2).map(([k,v]) => `${k}: ${String(v).slice(0,30)}`).join(' · ')}
        </span>
        <span style={{ fontSize: 11, color: '#8A8A82', marginLeft: 'auto', minWidth: 50, textAlign: 'right' }}>{call.duration_ms}ms</span>
        <span style={{ fontSize: 10, color: '#C8C8C0', minWidth: 60, textAlign: 'right', fontFamily: 'JetBrains Mono, monospace' }}>{new Date(call.timestamp).toLocaleTimeString()}</span>
        {expanded ? <ChevronUp size={11} style={{ color: '#C8C8C0' }} /> : <ChevronDown size={11} style={{ color: '#C8C8C0' }} />}
      </div>
      {expanded && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '0 16px 14px' }}>
          {[{ label: 'Args', content: JSON.stringify(call.args, null, 2), color: '#0A0A0A' },
            { label: call.error ? 'Error' : 'Result', content: call.error || JSON.stringify(call.result, null, 2)?.slice(0, 500), color: call.error ? '#DC2626' : '#0A0A0A' }
          ].map(({ label, content, color }) => (
            <div key={label}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
              <pre style={{ fontSize: 11, background: '#F3F3EF', border: '1px solid #E5E5E0', borderRadius: 6, padding: '8px 10px', overflow: 'auto', maxHeight: 120, margin: 0, fontFamily: 'JetBrains Mono, monospace', color }}>{content}</pre>
            </div>
          ))}
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
      const res  = await fetch(`/api/tools-proxy?tool=${selected}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(args)
      })
      const data = await res.json()
      setResult(data)
    } catch (err) { setError(err.message) }
    finally { setRunning(false) }
  }

  const inputStyle = { width: '100%', padding: '9px 12px', background: 'white', border: '1px solid #E5E5E0', borderRadius: 7, fontSize: 12, color: '#0A0A0A', fontFamily: 'Plus Jakarta Sans, sans-serif', outline: 'none' }

  return (
    <div className="card overflow-hidden">
      <div style={{ padding: '13px 16px', borderBottom: '1px solid #E5E5E0', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Wrench size={12} style={{ color: '#0041FF' }} />
        <span style={{ ...syne, fontSize: 11, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Tool Tester</span>
      </div>
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', marginBottom: 6 }}>Select Tool</div>
          <select value={selected} onChange={e => setSelected(e.target.value)} style={{ ...inputStyle }}>
            <option value="">— pick a tool —</option>
            {TOOL_GROUPS.map(g => (
              <optgroup key={g.label} label={g.label}>
                {g.tools.map(t => <option key={t} value={t}>{t}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', marginBottom: 6 }}>Arguments (JSON)</div>
          <textarea value={argsText} onChange={e => setArgsText(e.target.value)} rows={4}
            style={{ ...inputStyle, resize: 'none', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }} />
        </div>
        <button onClick={runTool} disabled={!selected || running} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          padding: '9px 0', border: '1px solid #0041FF', borderRadius: 7,
          background: '#EEF1FF', color: '#0041FF', fontSize: 12, fontWeight: 600, cursor: 'pointer',
          opacity: !selected || running ? 0.5 : 1,
        }}>
          {running ? <RefreshCw size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Play size={11} />}
          {running ? 'Running…' : 'Run Tool'}
        </button>
        {error && <div style={{ fontSize: 11, color: '#DC2626', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 6, padding: '8px 10px' }}>{error}</div>}
        {result && <pre style={{ fontSize: 11, background: '#F3F3EF', border: '1px solid #E5E5E0', borderRadius: 6, padding: '10px 12px', overflow: 'auto', maxHeight: 180, fontFamily: 'JetBrains Mono, monospace', color: '#0A0A0A', margin: 0 }}>{JSON.stringify(result, null, 2)}</pre>}
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
      const [c, t] = await Promise.all([
        fetch('/api/tool-calls?limit=100', { cache: 'no-store' }).then(r => r.json()),
        fetch('/api/tools-proxy', { cache: 'no-store' }).then(r => r.json()),
      ])
      setCalls((c.calls || []).reverse())
      setTools(t.tools || [])
    } catch {}
  }

  useEffect(() => {
    fetchData()
    if (live) intervalRef.current = setInterval(fetchData, 2000)
    return () => clearInterval(intervalRef.current)
  }, [live])

  const stats = {
    total: calls.length,
    ok: calls.filter(c => c.status === 'ok').length,
    errors: calls.filter(c => c.status === 'error').length,
    avg: calls.length ? Math.round(calls.reduce((a, c) => a + (c.duration_ms || 0), 0) / calls.length) : 0,
  }

  const filtered = filter === 'all' ? calls : calls.filter(c => c.status === filter || c.tool.includes(filter))

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Tool Server</div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', marginBottom: 4 }}>Tool Monitor</h1>
          <p style={{ fontSize: 13, color: '#8A8A82' }}>Live tool call feed · Test tools · Monitor errors</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setLive(l => !l)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '9px 14px',
            border: '1px solid', borderColor: live ? '#A7F3D0' : '#E5E5E0',
            background: live ? '#ECFDF5' : 'white', borderRadius: 8,
            color: live ? '#059669' : '#8A8A82', fontSize: 12, fontWeight: live ? 600 : 400, cursor: 'pointer',
          }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: live ? '#059669' : '#C8C8C0' }} className={live ? 'animate-pulse' : ''} />
            {live ? 'Live' : 'Paused'}
          </button>
          <button onClick={fetchData} style={{ padding: '9px 13px', border: '1px solid #E5E5E0', borderRadius: 8, background: 'white', cursor: 'pointer' }}>
            <RefreshCw size={12} style={{ color: '#8A8A82' }} />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid-stats" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Calls', value: stats.total, color: '#0041FF' },
          { label: 'Successful',  value: stats.ok,    color: '#059669' },
          { label: 'Errors',      value: stats.errors, color: '#DC2626' },
          { label: 'Avg Duration', value: `${stats.avg}ms`, color: '#D97706' },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{s.label}</div>
            <div style={{ ...syne, fontSize: 32, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-main-side">
        {/* Live feed */}
        <div className="card overflow-hidden">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '13px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Activity size={12} style={{ color: '#0041FF' }} />
              <span style={{ ...syne, fontSize: 11, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Live Tool Calls</span>
              {live && <span style={{ fontSize: 11, color: '#059669' }} className="animate-pulse">● LIVE</span>}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {['all', 'ok', 'error'].map(f => (
                <button key={f} onClick={() => setFilter(f)} style={{
                  padding: '4px 10px', borderRadius: 20, border: '1px solid',
                  borderColor: filter === f ? '#0041FF' : '#E5E5E0',
                  background: filter === f ? '#EEF1FF' : 'white',
                  color: filter === f ? '#0041FF' : '#8A8A82',
                  fontSize: 11, cursor: 'pointer', textTransform: 'capitalize',
                }}>{f}</button>
              ))}
            </div>
          </div>
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>
            {filtered.length === 0
              ? <div style={{ padding: 48, textAlign: 'center', fontSize: 13, color: '#8A8A82' }}>No tool calls yet. Run a pipeline to see activity.</div>
              : filtered.map(call => (
                <ToolCallRow key={call.id} call={call}
                  expanded={expanded === call.id}
                  onToggle={() => setExpanded(expanded === call.id ? null : call.id)} />
              ))
            }
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ToolTester tools={tools} />
          <div className="card overflow-hidden">
            <div style={{ padding: '13px 16px', borderBottom: '1px solid #E5E5E0', ...syne, fontSize: 11, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Available Tools
            </div>
            <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {TOOL_GROUPS.map(g => (
                <div key={g.label}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: g.color, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>{g.label}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {g.tools.map(t => {
                      const recent = calls.find(c => c.tool === t)
                      return (
                        <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: recent ? (recent.status === 'ok' ? '#059669' : '#DC2626') : '#E5E5E0' }} />
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#3D3D38', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{t}</span>
                          {recent && <span style={{ color: '#8A8A82', fontSize: 10 }}>{recent.duration_ms}ms</span>}
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
