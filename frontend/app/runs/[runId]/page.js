'use client'
import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import { RefreshCw, ArrowLeft, Terminal, FileJson, CheckCircle, XCircle, Clock, Loader, RotateCcw } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const STAGE_NAMES = {
  keyword_research:    { label: 'Keyword Research',     n: '01', file: '01_keywords.json' },
  serp_analysis:       { label: 'SERP Analysis',        n: '02', file: '02_serp.json' },
  content_outline:     { label: 'Content Outline',      n: '03', file: '03_outline.json' },
  content_writing:     { label: 'Content Writing',      n: '04', file: '04_content.json' },
  onpage_optimization: { label: 'On-Page Optimization', n: '05', file: '05_onpage.json' },
  internal_linking:    { label: 'Internal Linking',     n: '06', file: '06_links.json' },
  analyst_review:      { label: 'Analyst Review',       n: '07', file: '07_analyst.json' },
  memory_update:       { label: 'Memory Update',        n: '08', file: 'memory_update.json' },
}

const STATUS_STYLE = {
  done:    { color: '#059669', bg: '#ECFDF5', label: 'Done' },
  running: { color: '#0041FF', bg: '#EEF1FF', label: 'Running' },
  failed:  { color: '#DC2626', bg: '#FEF2F2', label: 'Failed' },
  pending: { color: '#8A8A82', bg: '#F3F3EF', label: 'Pending' },
}

function StageIcon({ status, size = 14 }) {
  if (status === 'done')    return <CheckCircle size={size} style={{ color: '#059669' }} />
  if (status === 'running') return <Loader size={size} style={{ color: '#0041FF', animation: 'spin 0.8s linear infinite' }} />
  if (status === 'failed')  return <XCircle size={size} style={{ color: '#DC2626' }} />
  return <Clock size={size} style={{ color: '#C8C8C0' }} />
}

function JSONView({ data }) {
  if (!data) return <div style={{ padding: 16, fontSize: 12, color: '#8A8A82' }}>No data</div>
  const str = JSON.stringify(data, null, 2)
  const html = str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
    .replace(/: (\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
    .replace(/: null/g, ': <span class="json-null">null</span>')
  return (
    <pre style={{ padding: 16, fontSize: 12, lineHeight: 1.7, overflow: 'auto', maxHeight: 360, fontFamily: 'JetBrains Mono, monospace', margin: 0 }}
      dangerouslySetInnerHTML={{ __html: html }} />
  )
}

export default function RunDetailPage({ params }) {
  const { runId } = params
  const [run, setRun]           = useState(null)
  const [logs, setLogs]         = useState([])
  const [activeTab, setActiveTab]   = useState('timeline')
  const [activeStage, setActiveStage] = useState(null)
  const [stageData, setStageData]   = useState({})
  const [resuming, setResuming]     = useState(false)
  const logRef = useRef(null)
  const esRef  = useRef(null)

  const fetchRun = async () => {
    const res  = await fetch(`/api/run/${runId}`)
    const data = await res.json()
    setRun(data)
  }

  const startStream = () => {
    if (esRef.current) esRef.current.close()
    const es = new EventSource(`/api/stream/${runId}`)
    esRef.current = es
    es.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log') {
        setLogs(prev => [...prev.slice(-500), msg.line])
        setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50)
      }
      if (msg.type === 'stage_update')
        setRun(prev => prev ? { ...prev, stages: { ...prev.stages, [msg.stage]: msg.status } } : prev)
      if (msg.type === 'done' || msg.type === 'failed') { fetchRun(); es.close() }
    }
    es.onerror = () => { es.close(); fetchRun() }
  }

  useEffect(() => {
    fetchRun()
    fetch(`/api/logs/${runId}?tail=100`).then(r => r.json()).then(d => setLogs(d.lines || []))
    return () => esRef.current?.close()
  }, [runId])

  useEffect(() => { if (run?.status === 'running') startStream() }, [run?.status])

  const loadStageData = async (key) => {
    if (stageData[key]) { setActiveStage(key); return }
    const cfg = STAGE_NAMES[key]
    if (!cfg) return
    const res  = await fetch(`/api/run/${runId}/stage/${cfg.n}`)
    const data = await res.json()
    setStageData(prev => ({ ...prev, [key]: data }))
    setActiveStage(key)
  }

  const handleResume = async () => {
    setResuming(true)
    await fetch(`/api/run/${runId}/resume`, { method: 'POST' })
    setResuming(false); fetchRun(); startStream()
  }

  if (!run) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 280 }}>
      <Loader size={22} style={{ color: '#0041FF', animation: 'spin 0.8s linear infinite' }} />
    </div>
  )

  const stages   = Object.entries(STAGE_NAMES)
  const doneCount = Object.values(run.stages || {}).filter(s => s === 'done').length
  const ss = STATUS_STYLE[run.status] || STATUS_STYLE.pending

  const Tab = ({ id, label }) => (
    <button onClick={() => setActiveTab(id)} style={{
      padding: '8px 16px', fontSize: 13, fontWeight: activeTab === id ? 600 : 400,
      color: activeTab === id ? '#0041FF' : '#8A8A82',
      borderBottom: activeTab === id ? '2px solid #0041FF' : '2px solid transparent',
      background: 'none', border: 'none', borderRadius: 0, cursor: 'pointer',
      transition: 'color 0.15s', marginBottom: -1,
    }}>
      {label}
    </button>
  )

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <Link href="/runs" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#8A8A82', textDecoration: 'none', marginBottom: 12 }}
            onMouseEnter={e => e.currentTarget.style.color = '#0041FF'}
            onMouseLeave={e => e.currentTarget.style.color = '#8A8A82'}>
            <ArrowLeft size={12} /> Back to Runs
          </Link>
          <h1 style={{ ...syne, fontSize: 28, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.4px', marginBottom: 8 }}>{run.task}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82' }}>{runId}</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 20, background: ss.bg, color: ss.color, fontSize: 11, fontWeight: 600 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: ss.color }} className={run.status === 'running' ? 'animate-pulse' : ''} />
              {ss.label}
            </span>
            <span style={{ fontSize: 12, color: '#8A8A82' }}>{doneCount}/{stages.length} stages</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={fetchRun} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 14px', border: '1px solid #E5E5E0', borderRadius: 8, background: 'white', fontSize: 12, color: '#3D3D38', cursor: 'pointer' }}>
            <RefreshCw size={11} /> Refresh
          </button>
          {run.status === 'failed' && (
            <button onClick={handleResume} disabled={resuming} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px',
              border: '1px solid #D97706', borderRadius: 8, background: '#FFFBEB',
              color: '#D97706', fontSize: 12, fontWeight: 600, cursor: 'pointer',
            }}>
              {resuming ? <Loader size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> : <RotateCcw size={11} />}
              Resume
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {run.error && (
        <div style={{ marginBottom: 16, background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, padding: '12px 16px', fontSize: 13, color: '#DC2626' }}>
          <strong>Error: </strong>{run.error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #E5E5E0', marginBottom: 24, display: 'flex', gap: 4 }}>
        <Tab id="timeline" label="Timeline" />
        <Tab id="outputs"  label="Stage Outputs" />
        <Tab id="logs"     label="Logs" />
      </div>

      {/* TIMELINE */}
      {activeTab === 'timeline' && (
        <div className="grid-stats" style={{ gap: 12 }}>
          {stages.map(([key, cfg]) => {
            const status = run.stages?.[key] || 'pending'
            const ss2 = STATUS_STYLE[status] || STATUS_STYLE.pending
            return (
              <div key={key}
                onClick={() => { setActiveTab('outputs'); loadStageData(key) }}
                style={{
                  background: 'white', border: `1px solid ${status === 'running' ? '#0041FF' : status === 'done' ? '#A7F3D0' : '#E5E5E0'}`,
                  borderRadius: 12, padding: 16, cursor: 'pointer',
                  boxShadow: status === 'running' ? '0 0 0 3px rgba(0,65,255,0.08)' : '0 1px 4px rgba(0,0,0,0.04)',
                  transition: 'all 0.15s',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82' }}>{cfg.n}</span>
                  <StageIcon status={status} size={13} />
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', marginBottom: 3 }}>{cfg.label}</div>
                <div style={{ fontSize: 10, color: '#8A8A82', fontFamily: 'JetBrains Mono, monospace' }}>{cfg.file}</div>
                {status === 'running' && (
                  <div style={{ marginTop: 10, height: 2, background: '#E5E5E0', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: '60%', background: '#0041FF', borderRadius: 2, animation: 'pulse 1.5s infinite' }} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* OUTPUTS */}
      {activeTab === 'outputs' && (
        <div className="grid-main-side">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {stages.map(([key, cfg]) => {
              const status = run.stages?.[key] || 'pending'
              return (
                <button key={key} onClick={() => loadStageData(key)} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px',
                  borderRadius: 8, fontSize: 12, fontWeight: activeStage === key ? 600 : 400,
                  color: activeStage === key ? '#0041FF' : '#3D3D38',
                  background: activeStage === key ? '#EEF1FF' : 'transparent',
                  border: '1px solid', borderColor: activeStage === key ? '#C7D2FE' : 'transparent',
                  cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                }}>
                  <StageIcon status={status} size={11} />
                  <span>{cfg.label}</span>
                </button>
              )
            })}
          </div>
          <div className="card overflow-hidden">
            {activeStage ? (
              <>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileJson size={13} style={{ color: '#0041FF' }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', fontFamily: 'JetBrains Mono, monospace' }}>{STAGE_NAMES[activeStage]?.file}</span>
                </div>
                {stageData[activeStage]?.error
                  ? <div style={{ padding: 16, fontSize: 13, color: '#DC2626' }}>{stageData[activeStage].error}</div>
                  : <JSONView data={stageData[activeStage]} />
                }
              </>
            ) : (
              <div style={{ padding: 48, textAlign: 'center', fontSize: 13, color: '#8A8A82' }}>Select a stage to view its output JSON</div>
            )}
          </div>
        </div>
      )}

      {/* LOGS */}
      {activeTab === 'logs' && (
        <div className="card overflow-hidden">
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Terminal size={13} style={{ color: '#0041FF' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', fontFamily: 'JetBrains Mono, monospace' }}>run.log</span>
              {run.status === 'running' && <span style={{ fontSize: 11, color: '#0041FF' }} className="animate-pulse">● LIVE</span>}
            </div>
            <span style={{ fontSize: 11, color: '#8A8A82' }}>{logs.length} lines</span>
          </div>
          <div ref={logRef} className="log-scroll" style={{ padding: 16, height: 400, overflowY: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, lineHeight: 1.8, background: '#FAFAF8' }}>
            {logs.length === 0
              ? <div style={{ color: '#8A8A82' }}>No logs yet…</div>
              : logs.map((line, i) => (
                  <div key={i} style={{
                    color: line.includes('ERROR') || line.includes('FAILED') ? '#DC2626'
                         : line.includes('DONE') || line.includes('SUCCESS') ? '#059669'
                         : line.includes('RUNNING') || line.includes('Starting') ? '#0041FF'
                         : line.includes('WARN') ? '#D97706'
                         : '#3D3D38'
                  }}>{line}</div>
                ))
            }
            {run.status === 'running' && <div className="cursor-blink" />}
          </div>
        </div>
      )}
    </div>
  )
}
