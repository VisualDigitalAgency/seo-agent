'use client'
import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import {
  RefreshCw, ArrowLeft, Terminal, FileJson,
  CheckCircle, XCircle, Clock, Loader, RotateCcw,
  Copy, Download, FileText, Code, Eye, Check
} from 'lucide-react'

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

// ── Copy button with "Copied!" flash ──────────────────────────────────────────
function CopyBtn({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button onClick={handleCopy} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '7px 14px', border: '1px solid',
      borderColor: copied ? '#A7F3D0' : '#E5E5E0',
      background: copied ? '#ECFDF5' : 'white',
      color: copied ? '#059669' : '#3D3D38',
      borderRadius: 7, fontSize: 12, fontWeight: 500, cursor: 'pointer',
      transition: 'all 0.2s',
    }}>
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

// ── Download helper ────────────────────────────────────────────────────────────
function download(filename, content) {
  const blob = new Blob([content], { type: 'text/plain' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── Content Output panel ──────────────────────────────────────────────────────
function ContentOutput({ data, task }) {
  const [view, setView] = useState('preview') // preview | html | markdown

  if (!data) return (
    <div style={{ padding: 48, textAlign: 'center', fontSize: 13, color: '#8A8A82' }}>
      Content not available yet — complete the Content Writing stage first.
    </div>
  )

  const html     = data.article_html     || ''
  const markdown = data.article_markdown || ''
  const title    = data.title            || task || 'article'
  const slug     = data.url_slug         || 'article'

  const ViewBtn = ({ id, icon: Icon, label }) => (
    <button onClick={() => setView(id)} style={{
      display: 'flex', alignItems: 'center', gap: 5,
      padding: '6px 12px', borderRadius: 7, border: '1px solid',
      borderColor: view === id ? '#0041FF' : '#E5E5E0',
      background: view === id ? '#EEF1FF' : 'white',
      color: view === id ? '#0041FF' : '#8A8A82',
      fontSize: 12, fontWeight: view === id ? 600 : 400, cursor: 'pointer',
    }}>
      <Icon size={11} /> {label}
    </button>
  )

  return (
    <div>
      {/* Meta strip */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { label: 'Title',            value: data.title },
            { label: 'Meta Title',       value: data.meta_title },
            { label: 'URL Slug',         value: `/${data.url_slug}` },
            { label: 'Meta Description', value: data.meta_description },
            { label: 'Word Count',       value: data.word_count ? `~${data.word_count.toLocaleString()} words` : '—' },
            { label: 'Primary KW Count', value: data.primary_keyword_count ? `${data.primary_keyword_count}×` : '—' },
          ].map(m => (
            <div key={m.label} style={{ minWidth: 0 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>{m.label}</div>
              <div style={{ fontSize: 12, color: '#0A0A0A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.value || '—'}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Viewer card */}
      <div className="card overflow-hidden">
        {/* Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <ViewBtn id="preview"  icon={Eye}      label="Preview" />
            <ViewBtn id="html"     icon={Code}     label="HTML" />
            <ViewBtn id="markdown" icon={FileText} label="Markdown" />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {view === 'html' && (
              <>
                <CopyBtn text={html} label="Copy HTML" />
                <button onClick={() => download(`${slug}.html`, html)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', border: '1px solid #C7D2FE', background: '#EEF1FF', color: '#0041FF', borderRadius: 7, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>
                  <Download size={12} /> Download .html
                </button>
              </>
            )}
            {view === 'markdown' && (
              <>
                <CopyBtn text={markdown} label="Copy MD" />
                <button onClick={() => download(`${slug}.md`, markdown)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', border: '1px solid #C7D2FE', background: '#EEF1FF', color: '#0041FF', borderRadius: 7, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>
                  <Download size={12} /> Download .md
                </button>
              </>
            )}
            {view === 'preview' && html && (
              <CopyBtn text={html} label="Copy HTML" />
            )}
          </div>
        </div>

        {/* Content area */}
        {view === 'preview' && (
          <div
            style={{ padding: '28px 36px', maxHeight: 640, overflowY: 'auto', lineHeight: 1.8, color: '#0A0A0A' }}
            className="article-preview"
            dangerouslySetInnerHTML={{ __html: html || '<p style="color:#8A8A82">No HTML content available.</p>' }}
          />
        )}
        {view === 'html' && (
          <pre style={{ padding: 20, maxHeight: 560, overflowY: 'auto', fontSize: 12, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.7, color: '#0A0A0A', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {html || 'No HTML content available.'}
          </pre>
        )}
        {view === 'markdown' && (
          <pre style={{ padding: 20, maxHeight: 560, overflowY: 'auto', fontSize: 12, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.7, color: '#0A0A0A', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {markdown || 'No Markdown content available.'}
          </pre>
        )}
      </div>
      </div>

      {/* FAQ Schema */}
      {data.faq_schema && (
        <div className="card overflow-hidden" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code size={12} style={{ color: '#7C3AED' }} />
              <span style={{ ...syne, fontSize: 11, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>FAQ Schema (JSON-LD)</span>
            </div>
            <CopyBtn text={JSON.stringify(data.faq_schema, null, 2)} label="Copy Schema" />
          </div>
          <pre style={{ padding: 16, fontSize: 11, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.7, maxHeight: 240, overflow: 'auto', margin: 0, color: '#0A0A0A' }}>
            {JSON.stringify(data.faq_schema, null, 2)}
          </pre>
        </div>
      )}
    </div>  
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function RunDetailPage({ params }) {
  const { runId } = params
  const [run, setRun]               = useState(null)
  const [logs, setLogs]             = useState([])
  const [activeTab, setActiveTab]   = useState('timeline')
  const [activeStage, setActiveStage] = useState(null)
  const [stageData, setStageData]   = useState({})
  const [contentData, setContentData] = useState(null)
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
      if (msg.type === 'done' || msg.type === 'failed') {
        fetchRun()
        es.close()
        // Auto-load content when run completes
        loadContentData()
      }
    }
    es.onerror = () => { es.close(); fetchRun() }
  }

  const loadStageData = async (key) => {
    if (stageData[key]) { setActiveStage(key); return }
    const cfg = STAGE_NAMES[key]
    if (!cfg) return
    const res  = await fetch(`/api/run/${runId}/stage/${cfg.n}`)
    const data = await res.json()
    setStageData(prev => ({ ...prev, [key]: data }))
    setActiveStage(key)
  }

  const loadContentData = async () => {
    try {
      const cfg = STAGE_NAMES['content_writing']
      const res  = await fetch(`/api/run/${runId}/stage/${cfg.n}`)
      const data = await res.json()
      if (data && !data.error) setContentData(data)
    } catch {}
  }

  useEffect(() => {
    fetchRun()
    fetch(`/api/logs/${runId}?tail=100`).then(r => r.json()).then(d => setLogs(d.lines || []))
    loadContentData()
    return () => esRef.current?.close()
  }, [runId])

  useEffect(() => { if (run?.status === 'running') startStream() }, [run?.status])

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

  const stages    = Object.entries(STAGE_NAMES)
  const doneCount = Object.values(run.stages || {}).filter(s => s === 'done').length
  const ss        = STATUS_STYLE[run.status] || STATUS_STYLE.pending
  const isDone    = run.status === 'done'

  const Tab = ({ id, label, badge }) => (
    <button onClick={() => { setActiveTab(id); if (id === 'content') loadContentData() }} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '8px 16px', fontSize: 13, fontWeight: activeTab === id ? 600 : 400,
      color: activeTab === id ? '#0041FF' : '#8A8A82',
      borderBottom: activeTab === id ? '2px solid #0041FF' : '2px solid transparent',
      background: 'none', border: 'none', borderRadius: 0, cursor: 'pointer',
      transition: 'color 0.15s', marginBottom: -1,
    }}>
      {label}
      {badge && <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 10, background: '#059669', color: 'white' }}>{badge}</span>}
    </button>
  )

  return (
    <div className="animate-fade-in">
      {/* Article preview styles */}
      <style>{`
        .article-preview h1 { font-size: 26px; font-weight: 700; margin: 0 0 16px; color: #0A0A0A; font-family: Syne, sans-serif; line-height: 1.2; }
        .article-preview h2 { font-size: 20px; font-weight: 700; margin: 28px 0 12px; color: #0A0A0A; font-family: Syne, sans-serif; }
        .article-preview h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; color: #3D3D38; }
        .article-preview p  { margin: 0 0 14px; color: #3D3D38; font-size: 15px; }
        .article-preview ul, .article-preview ol { margin: 0 0 14px; padding-left: 22px; }
        .article-preview li { margin-bottom: 6px; color: #3D3D38; font-size: 15px; }
        .article-preview strong { color: #0A0A0A; font-weight: 600; }
        .article-preview a  { color: #0041FF; text-decoration: none; }
        .article-preview a:hover { text-decoration: underline; }
        .article-preview blockquote { border-left: 3px solid #0041FF; margin: 0 0 14px; padding: 8px 16px; background: #EEF1FF; border-radius: 0 6px 6px 0; }
      `}</style>

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
            <button onClick={handleResume} disabled={resuming} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px', border: '1px solid #D97706', borderRadius: 8, background: '#FFFBEB', color: '#D97706', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
              {resuming ? <Loader size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> : <RotateCcw size={11} />}
              Resume
            </button>
          )}
        </div>
      </div>

      {run.error && (
        <div style={{ marginBottom: 16, background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, padding: '12px 16px', fontSize: 13, color: '#DC2626' }}>
          <strong>Error: </strong>{run.error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #E5E5E0', marginBottom: 24, display: 'flex', gap: 4 }}>
        <Tab id="timeline" label="Timeline" />
        <Tab id="content"  label="Content Output" badge={isDone && contentData ? 'NEW' : null} />
        <Tab id="outputs"  label="Stage Outputs" />
        <Tab id="logs"     label="Logs" />
      </div>

      {/* ── TIMELINE ── */}
      {activeTab === 'timeline' && (
        <div>
          {isDone && contentData && (
            <div style={{ marginBottom: 20, background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 10, padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <CheckCircle size={16} style={{ color: '#059669' }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#059669' }}>Run complete — article ready</div>
                  <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
                    {contentData.word_count ? `~${contentData.word_count.toLocaleString()} words ·` : ''} HTML & Markdown available for download
                  </div>
                </div>
              </div>
              <button onClick={() => setActiveTab('content')} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#059669', color: 'white', border: 'none', borderRadius: 7, fontSize: 12, fontWeight: 600, cursor: 'pointer', ...syne }}>
                <Download size={12} /> View Content
              </button>
            </div>
          )}
          <div className="grid-stats" style={{ gap: 12 }}>
            {stages.map(([key, cfg]) => {
              const status = run.stages?.[key] || 'pending'
              const ss2 = STATUS_STYLE[status] || STATUS_STYLE.pending
              return (
                <div key={key}
                  onClick={() => { setActiveTab(key === 'content_writing' ? 'content' : 'outputs'); key === 'content_writing' ? loadContentData() : loadStageData(key) }}
                  style={{
                    background: 'white', border: `1px solid ${status === 'running' ? '#0041FF' : status === 'done' ? '#A7F3D0' : '#E5E5E0'}`,
                    borderRadius: 12, padding: 16, cursor: 'pointer',
                    boxShadow: status === 'running' ? '0 0 0 3px rgba(0,65,255,0.08)' : '0 1px 4px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)'}
                  onMouseLeave={e => e.currentTarget.style.boxShadow = status === 'running' ? '0 0 0 3px rgba(0,65,255,0.08)' : '0 1px 4px rgba(0,0,0,0.04)'}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82' }}>{cfg.n}</span>
                    <StageIcon status={status} size={13} />
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', marginBottom: 3 }}>{cfg.label}</div>
                  <div style={{ fontSize: 10, color: '#8A8A82', fontFamily: 'JetBrains Mono, monospace' }}>{cfg.file}</div>
                  {key === 'content_writing' && status === 'done' && (
                    <div style={{ marginTop: 8, fontSize: 10, color: '#059669', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Download size={9} /> HTML + MD ready
                    </div>
                  )}
                  {status === 'running' && (
                    <div style={{ marginTop: 10, height: 2, background: '#E5E5E0', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: '60%', background: '#0041FF', borderRadius: 2, animation: 'pulse 1.5s infinite' }} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── CONTENT OUTPUT ── */}
      {activeTab === 'content' && (
        <ContentOutput data={contentData} task={run.task} />
      )}

      {/* ── STAGE OUTPUTS ── */}
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
                <div style={{ padding: '12px 16px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FileJson size={13} style={{ color: '#0041FF' }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', fontFamily: 'JetBrains Mono, monospace' }}>{STAGE_NAMES[activeStage]?.file}</span>
                  </div>
                  {stageData[activeStage] && !stageData[activeStage].error && (
                    <CopyBtn text={JSON.stringify(stageData[activeStage], null, 2)} label="Copy JSON" />
                  )}
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

      {/* ── LOGS ── */}
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
