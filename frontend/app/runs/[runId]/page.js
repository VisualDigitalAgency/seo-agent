'use client'
import { useEffect, useState, useRef, use } from 'react'
import Link from 'next/link'
import { RefreshCw, ArrowLeft, Terminal, FileJson, CheckCircle, XCircle, Clock, Loader, RotateCcw } from 'lucide-react'

const STAGE_NAMES = {
  keyword_research:    { label: 'Keyword Research',    n: '01', file: '01_keywords.json' },
  serp_analysis:       { label: 'SERP Analysis',       n: '02', file: '02_serp.json' },
  content_outline:     { label: 'Content Outline',     n: '03', file: '03_outline.json' },
  content_writing:     { label: 'Content Writing',     n: '04', file: '04_content.json' },
  onpage_optimization: { label: 'On-Page Optimization',n: '05', file: '05_onpage.json' },
  internal_linking:    { label: 'Internal Linking',    n: '06', file: '06_links.json' },
  analyst_review:      { label: 'Analyst Review',      n: '07', file: '07_analyst.json' },
  memory_update:       { label: 'Memory Update',       n: '08', file: 'memory_update.json' },
}

function JSONView({ data }) {
  if (!data) return <div className="text-xs text-muted p-4">No data</div>
  const str = JSON.stringify(data, null, 2)
  const highlighted = str
    .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
    .replace(/: (\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
    .replace(/: null/g, ': <span class="json-null">null</span>')
  return (
    <pre className="p-4 text-xs leading-relaxed overflow-auto max-h-80 font-mono"
      dangerouslySetInnerHTML={{ __html: highlighted }} />
  )
}

export default function RunDetailPage({ params }) {
  const { runId } = use(params)
  const [run, setRun] = useState(null)
  const [logs, setLogs] = useState([])
  const [activeTab, setActiveTab] = useState('timeline')
  const [activeStage, setActiveStage] = useState(null)
  const [stageData, setStageData] = useState({})
  const [resuming, setResuming] = useState(false)
  const logRef = useRef(null)
  const eventSourceRef = useRef(null)

  // Fetch run status
  const fetchRun = async () => {
    const res = await fetch(`/api/run/${runId}`)
    const data = await res.json()
    setRun(data)
  }

  // Start SSE stream
  const startStream = () => {
    if (eventSourceRef.current) eventSourceRef.current.close()
    const es = new EventSource(`/api/stream/${runId}`)
    eventSourceRef.current = es

    es.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log') {
        setLogs(prev => [...prev.slice(-500), msg.line])
        setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50)
      }
      if (msg.type === 'stage_update') {
        setRun(prev => prev ? { ...prev, stages: { ...prev.stages, [msg.stage]: msg.status } } : prev)
      }
      if (msg.type === 'done' || msg.type === 'failed') {
        fetchRun()
        es.close()
      }
    }
    es.onerror = () => { es.close(); fetchRun() }
  }

  useEffect(() => {
    fetchRun()
    // Load recent logs
    fetch(`/api/logs/${runId}?tail=100`)
      .then(r => r.json())
      .then(d => setLogs(d.lines || []))

    return () => eventSourceRef.current?.close()
  }, [runId])

  useEffect(() => {
    if (run?.status === 'running') startStream()
  }, [run?.status])

  const loadStageData = async (stageKey) => {
    if (stageData[stageKey]) { setActiveStage(stageKey); return }
    const stageCfg = STAGE_NAMES[stageKey]
    if (!stageCfg) return
    const stageNum = stageCfg.n
    const res = await fetch(`/api/run/${runId}/stage/${stageNum}`)
    const data = await res.json()
    setStageData(prev => ({ ...prev, [stageKey]: data }))
    setActiveStage(stageKey)
  }

  const handleResume = async () => {
    setResuming(true)
    await fetch(`/api/run/${runId}/resume`, { method: 'POST' })
    setResuming(false)
    fetchRun()
    startStream()
  }

  if (!run) return (
    <div className="flex items-center justify-center h-64">
      <Loader size={20} className="animate-spin text-accent" />
    </div>
  )

  const stages = Object.entries(STAGE_NAMES)
  const completedCount = Object.values(run.stages || {}).filter(s => s === 'done').length

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link href="/runs" className="flex items-center gap-1.5 text-xs text-muted hover:text-accent mb-3 transition-colors">
            <ArrowLeft size={11} /> Back to Runs
          </Link>
          <h1 className="font-sans text-2xl font-bold text-white tracking-tight">{run.task}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-muted font-mono">{runId}</span>
            <StatusBadge status={run.status} />
            <span className="text-xs text-muted">{completedCount}/{stages.length} stages</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchRun} className="flex items-center gap-1.5 px-3 py-2 text-xs text-muted border border-border rounded hover:text-white transition-colors">
            <RefreshCw size={11} /> Refresh
          </button>
          {run.status === 'failed' && (
            <button onClick={handleResume} disabled={resuming}
              className="flex items-center gap-1.5 px-4 py-2 bg-accent4/10 text-accent4 text-xs border border-accent4/30 rounded hover:bg-accent4/20 transition-colors disabled:opacity-50">
              {resuming ? <Loader size={11} className="animate-spin" /> : <RotateCcw size={11} />}
              Resume from {run.resume_from || 'failed stage'}
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {run.error && (
        <div className="mb-4 bg-accent5/10 border border-accent5/30 rounded px-4 py-3 text-xs text-accent5">
          <span className="font-bold">Error: </span>{run.error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border pb-1">
        {[
          { id: 'timeline', label: 'Timeline' },
          { id: 'outputs', label: 'Stage Outputs' },
          { id: 'logs', label: 'Logs' },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs rounded-t transition-colors
              ${activeTab === tab.id ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* TIMELINE TAB */}
      {activeTab === 'timeline' && (
        <div className="grid grid-cols-3 gap-4">
          {stages.map(([key, cfg]) => {
            const status = run.stages?.[key] || 'pending'
            return (
              <div key={key} className={`bg-surface border rounded p-4 transition-all cursor-pointer
                ${status === 'done' ? 'border-accent3/30' : status === 'running' ? 'border-accent/40 shadow-[0_0_12px_rgba(0,229,255,0.1)]' : status === 'failed' ? 'border-accent5/30' : 'border-border'}`}
                onClick={() => { setActiveTab('outputs'); loadStageData(key) }}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-muted font-mono">{cfg.n}</span>
                  <StageIcon status={status} />
                </div>
                <div className="text-xs font-bold text-white mb-1">{cfg.label}</div>
                <div className="text-xs text-muted">{cfg.file}</div>
                {status === 'running' && (
                  <div className="mt-3 h-0.5 bg-dim rounded-full overflow-hidden">
                    <div className="h-full bg-accent rounded-full animate-pulse w-2/3" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* OUTPUTS TAB */}
      {activeTab === 'outputs' && (
        <div className="grid grid-cols-4 gap-4">
          <div className="col-span-1 space-y-1">
            {stages.map(([key, cfg]) => {
              const status = run.stages?.[key] || 'pending'
              return (
                <button key={key} onClick={() => loadStageData(key)}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs transition-colors flex items-center gap-2
                    ${activeStage === key ? 'bg-accent/10 border border-accent/20 text-accent' : 'text-muted hover:text-white hover:bg-surface2 border border-transparent'}`}>
                  <StageIcon status={status} size={10} />
                  <span>{cfg.label}</span>
                </button>
              )
            })}
          </div>
          <div className="col-span-3 bg-surface border border-border rounded overflow-hidden">
            {activeStage ? (
              <>
                <div className="px-4 py-3 border-b border-border bg-surface2 flex items-center gap-2">
                  <FileJson size={12} className="text-accent" />
                  <span className="text-xs font-bold text-white">{STAGE_NAMES[activeStage]?.file}</span>
                </div>
                {stageData[activeStage]?.error ? (
                  <div className="p-4 text-xs text-accent5">{stageData[activeStage].error}</div>
                ) : (
                  <JSONView data={stageData[activeStage]} />
                )}
              </>
            ) : (
              <div className="p-8 text-center text-xs text-muted">Select a stage to view its output JSON</div>
            )}
          </div>
        </div>
      )}

      {/* LOGS TAB */}
      {activeTab === 'logs' && (
        <div className="bg-surface border border-border rounded overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-surface2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal size={12} className="text-accent" />
              <span className="text-xs font-bold text-white">run.log</span>
              {run.status === 'running' && (
                <span className="text-xs text-accent animate-pulse">● LIVE</span>
              )}
            </div>
            <span className="text-xs text-muted">{logs.length} lines</span>
          </div>
          <div ref={logRef} className="p-4 h-96 overflow-auto log-scroll font-mono text-xs leading-relaxed space-y-0.5">
            {logs.length === 0 ? (
              <div className="text-muted">No logs yet...</div>
            ) : (
              logs.map((line, i) => (
                <div key={i} className={`
                  ${line.includes('ERROR') || line.includes('FAILED') ? 'text-accent5' :
                    line.includes('DONE') || line.includes('SUCCESS') || line.includes('✓') ? 'text-accent3' :
                    line.includes('RUNNING') || line.includes('Starting') ? 'text-accent' :
                    line.includes('WARN') ? 'text-accent4' : 'text-muted'}
                `}>{line}</div>
              ))
            )}
            {run.status === 'running' && <div className="text-accent cursor-blink" />}
          </div>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const cfg = {
    done: 'bg-accent3/10 border-accent3/30 text-accent3',
    running: 'bg-accent/10 border-accent/30 text-accent',
    failed: 'bg-accent5/10 border-accent5/30 text-accent5',
    pending: 'bg-dim/20 border-dim/30 text-muted',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${cfg[status] || cfg.pending}`}>
      {status}
    </span>
  )
}

function StageIcon({ status, size = 14 }) {
  if (status === 'done') return <CheckCircle size={size} className="text-accent3" />
  if (status === 'running') return <Loader size={size} className="text-accent animate-spin" />
  if (status === 'failed') return <XCircle size={size} className="text-accent5" />
  return <Clock size={size} className="text-dim" />
}
