'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Play, RefreshCw, Trash2, ArrowRight, CheckCircle, XCircle, Clock, Loader } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const STATUS = {
  done:    { label: 'Done',    color: '#059669', bg: '#ECFDF5' },
  running: { label: 'Running', color: '#0041FF', bg: '#EEF1FF' },
  failed:  { label: 'Failed',  color: '#DC2626', bg: '#FEF2F2' },
  pending: { label: 'Pending', color: '#8A8A82', bg: '#F3F3EF' },
}

function StageBar({ stages }) {
  const list  = Object.values(stages || {})
  const total = list.length || 7
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {Array.from({ length: total }).map((_, i) => {
        const s = list[i]
        const c = s === 'done' ? '#059669' : s === 'running' ? '#0041FF' : s === 'failed' ? '#DC2626' : '#E5E5E0'
        return <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: c }} />
      })}
    </div>
  )
}

function FilterBtn({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: '6px 14px', borderRadius: 20, border: '1px solid',
      borderColor: active ? '#0041FF' : '#E5E5E0',
      background: active ? '#EEF1FF' : 'white',
      color: active ? '#0041FF' : '#8A8A82',
      fontSize: 12, fontWeight: active ? 600 : 400,
      cursor: 'pointer', transition: 'all 0.15s',
    }}>
      {label}
    </button>
  )
}

export default function RunsPage() {
  const [runs, setRuns]       = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)
  const [resuming, setResuming] = useState(null)
  const [filter, setFilter]   = useState('all')

  const fetchRuns = () => {
    setLoading(true)
    fetch('/api/runs').then(r => r.json())
      .then(d => { setRuns(d.runs || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchRuns() }, [])

  const handleDelete = async (id) => {
    if (!confirm(`Delete run ${id}?`)) return
    setDeleting(id)
    await fetch(`/api/run/${id}`, { method: 'DELETE' })
    setDeleting(null); fetchRuns()
  }

  const handleResume = async (id) => {
    setResuming(id)
    await fetch(`/api/run/${id}/resume`, { method: 'POST' })
    setResuming(null)
    window.location.href = `/runs/${id}`
  }

  const filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter)
  const sorted   = [...filtered].sort((a, b) => b.run_id.localeCompare(a.run_id))

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', marginBottom: 4 }}>Runs</h1>
          <p style={{ fontSize: 13, color: '#8A8A82' }}>{runs.length} total runs</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={fetchRuns} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px',
            background: 'white', border: '1px solid #E5E5E0', borderRadius: 8,
            fontSize: 12, color: '#3D3D38', cursor: 'pointer',
          }}>
            <RefreshCw size={12} /> Refresh
          </button>
          <Link href="/task" style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px',
            background: '#0041FF', color: 'white', borderRadius: 8, textDecoration: 'none',
            ...syne, fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>
            <Play size={12} /> New Run
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['all', 'running', 'done', 'failed', 'pending'].map(f => (
          <FilterBtn
            key={f}
            label={`${f.charAt(0).toUpperCase() + f.slice(1)} ${f === 'all' ? `(${runs.length})` : `(${runs.filter(r => r.status === f).length})`}`}
            active={filter === f}
            onClick={() => setFilter(f)}
          />
        ))}
      </div>

      {/* Table */}
      <div className="table-scroll"><div className="card overflow-hidden" style={{ minWidth: 640 }}>
        {/* Header row */}
        <div style={{
          display: 'grid', gridTemplateColumns: '80px 1fr 160px 140px 120px',
          padding: '10px 20px', borderBottom: '1px solid #E5E5E0',
          background: '#FAFAF8',
        }}>
          {['Status', 'Task', 'Run ID', 'Progress', 'Actions'].map((h, i) => (
            <div key={h} style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.07em', textTransform: 'uppercase', textAlign: i === 4 ? 'right' : 'left' }}>{h}</div>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: '#8A8A82', fontSize: 13 }}>Loading runs…</div>
        ) : sorted.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <div style={{ fontSize: 13, color: '#8A8A82', marginBottom: 10 }}>No runs found</div>
            <Link href="/task" style={{ fontSize: 13, color: '#0041FF', textDecoration: 'none', fontWeight: 500 }}>Create your first run →</Link>
          </div>
        ) : sorted.map(run => {
          const cfg  = STATUS[run.status] || STATUS.pending
          const done = Object.values(run.stages || {}).filter(s => s === 'done').length
          const total = Object.keys(run.stages || {}).length || 7
          return (
            <div
              key={run.run_id}
              style={{ display: 'grid', gridTemplateColumns: '80px 1fr 160px 140px 120px', padding: '14px 20px', borderBottom: '1px solid #E5E5E0', alignItems: 'center', transition: 'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#FAFAF8'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              {/* Status */}
              <div>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 20, background: cfg.bg, color: cfg.color, fontSize: 11, fontWeight: 600 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.color, flexShrink: 0 }}
                    className={run.status === 'running' ? 'animate-pulse' : ''} />
                  {cfg.label}
                </span>
              </div>
              {/* Task */}
              <div style={{ paddingRight: 16 }}>
                <Link href={`/runs/${run.run_id}`} style={{ fontSize: 13, fontWeight: 500, color: '#0A0A0A', textDecoration: 'none' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#0041FF'}
                  onMouseLeave={e => e.currentTarget.style.color = '#0A0A0A'}>
                  {run.task}
                </Link>
                {run.error && <div style={{ fontSize: 11, color: '#DC2626', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{run.error}</div>}
              </div>
              {/* Run ID */}
              <div style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{run.run_id}</div>
              {/* Progress */}
              <div>
                <StageBar stages={run.stages} />
                <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 4 }}>{done}/{total} stages</div>
              </div>
              {/* Actions */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                {run.status === 'failed' && (
                  <button onClick={() => handleResume(run.run_id)} disabled={resuming === run.run_id}
                    style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', border: '1px solid #D97706', borderRadius: 6, background: '#FFFBEB', color: '#D97706', fontSize: 11, cursor: 'pointer' }}>
                    {resuming === run.run_id ? <Loader size={9} style={{ animation: 'spin 0.7s linear infinite' }} /> : <RefreshCw size={9} />}
                    Resume
                  </button>
                )}
                <Link href={`/runs/${run.run_id}`}
                  style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', border: '1px solid #E5E5E0', borderRadius: 6, color: '#3D3D38', fontSize: 11, textDecoration: 'none' }}>
                  View <ArrowRight size={9} />
                </Link>
                <button onClick={() => handleDelete(run.run_id)} disabled={deleting === run.run_id}
                  style={{ padding: '5px 8px', border: '1px solid transparent', borderRadius: 6, color: '#C8C8C0', background: 'none', cursor: 'pointer', transition: 'all 0.15s' }}
                  onMouseEnter={e => { e.currentTarget.style.color = '#DC2626'; e.currentTarget.style.borderColor = '#FECACA'; e.currentTarget.style.background = '#FEF2F2' }}
                  onMouseLeave={e => { e.currentTarget.style.color = '#C8C8C0'; e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.background = 'none' }}>
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div></div>
  )
}
