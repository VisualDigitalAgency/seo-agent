'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Play, RefreshCw, Trash2, ArrowRight, Clock, CheckCircle, XCircle, Loader } from 'lucide-react'

const STATUS_CONFIG = {
  done: { label: 'Done', color: 'text-accent3', bg: 'bg-accent3/10 border-accent3/20', dot: 'bg-accent3', icon: CheckCircle },
  running: { label: 'Running', color: 'text-accent', bg: 'bg-accent/10 border-accent/20', dot: 'bg-accent animate-pulse', icon: Loader },
  failed: { label: 'Failed', color: 'text-accent5', bg: 'bg-accent5/10 border-accent5/20', dot: 'bg-accent5', icon: XCircle },
  pending: { label: 'Pending', color: 'text-muted', bg: 'bg-dim/10 border-dim/20', dot: 'bg-dim', icon: Clock },
}

function StageBar({ stages }) {
  const stageList = Object.values(stages || {})
  const total = stageList.length || 7
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: total }).map((_, i) => {
        const s = stageList[i]
        const color = s === 'done' ? 'bg-accent3' : s === 'running' ? 'bg-accent' : s === 'failed' ? 'bg-accent5' : 'bg-dim'
        return <div key={i} className={`h-1.5 flex-1 rounded-sm ${color}`} />
      })}
    </div>
  )
}

export default function RunsPage() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)
  const [resuming, setResuming] = useState(null)
  const [filter, setFilter] = useState('all')

  const fetchRuns = () => {
    setLoading(true)
    fetch('/api/runs')
      .then(r => r.json())
      .then(data => { setRuns(data.runs || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchRuns() }, [])

  const handleDelete = async (runId) => {
    if (!confirm(`Delete run ${runId}?`)) return
    setDeleting(runId)
    await fetch(`/api/run/${runId}`, { method: 'DELETE' })
    setDeleting(null)
    fetchRuns()
  }

  const handleResume = async (runId) => {
    setResuming(runId)
    await fetch(`/api/run/${runId}/resume`, { method: 'POST' })
    setResuming(null)
    window.location.href = `/runs/${runId}`
  }

  const filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter)
  const sorted = [...filtered].sort((a, b) => b.run_id.localeCompare(a.run_id))

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Runs</h1>
          <p className="text-muted text-xs mt-1">{runs.length} total runs</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchRuns} className="flex items-center gap-2 px-3 py-2 text-xs text-muted border border-border rounded hover:text-white hover:border-accent/30 transition-colors">
            <RefreshCw size={12} /> Refresh
          </button>
          <Link href="/task" className="flex items-center gap-2 px-4 py-2 bg-accent text-bg text-xs font-bold rounded hover:bg-accent/90 transition-colors">
            <Play size={12} /> NEW RUN
          </Link>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6">
        {['all', 'running', 'done', 'failed', 'pending'].map(f => (
          <button key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs rounded transition-colors capitalize
              ${filter === f ? 'bg-accent/10 text-accent border border-accent/20' : 'text-muted hover:text-white border border-transparent'}`}>
            {f} {f === 'all' ? `(${runs.length})` : `(${runs.filter(r => r.status === f).length})`}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-surface border border-border rounded overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-4 py-2.5 border-b border-border bg-surface2 text-xs text-muted uppercase tracking-widest">
          <div className="col-span-1">Status</div>
          <div className="col-span-4">Task</div>
          <div className="col-span-2">Run ID</div>
          <div className="col-span-3">Progress</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-muted">Loading runs...</div>
        ) : sorted.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-xs text-muted mb-2">No runs found</div>
            <Link href="/task" className="text-xs text-accent hover:underline">Create your first run →</Link>
          </div>
        ) : (
          sorted.map(run => {
            const cfg = STATUS_CONFIG[run.status] || STATUS_CONFIG.pending
            const Icon = cfg.icon
            const completedStages = Object.values(run.stages || {}).filter(s => s === 'done').length
            const totalStages = Object.keys(run.stages || {}).length || 7

            return (
              <div key={run.run_id} className="grid grid-cols-12 gap-4 px-4 py-3.5 border-b border-border/50 hover:bg-surface2/50 transition-colors items-center group">
                <div className="col-span-1">
                  <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded border ${cfg.bg} ${cfg.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                    {cfg.label}
                  </span>
                </div>
                <div className="col-span-4">
                  <Link href={`/runs/${run.run_id}`} className="text-xs text-white hover:text-accent transition-colors">
                    {run.task}
                  </Link>
                  {run.error && (
                    <div className="text-xs text-accent5 truncate mt-0.5">{run.error}</div>
                  )}
                </div>
                <div className="col-span-2">
                  <span className="text-xs text-muted font-mono">{run.run_id}</span>
                </div>
                <div className="col-span-3">
                  <div className="mb-1"><StageBar stages={run.stages} /></div>
                  <div className="text-xs text-muted">{completedStages}/{totalStages} stages</div>
                </div>
                <div className="col-span-2 flex items-center justify-end gap-2">
                  {run.status === 'failed' && (
                    <button onClick={() => handleResume(run.run_id)} disabled={resuming === run.run_id}
                      className="text-xs text-accent4 hover:text-white border border-accent4/30 px-2 py-1 rounded hover:bg-accent4/10 transition-colors disabled:opacity-50 flex items-center gap-1">
                      {resuming === run.run_id ? <Loader size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                      Resume
                    </button>
                  )}
                  <Link href={`/runs/${run.run_id}`}
                    className="text-xs text-muted hover:text-accent border border-border px-2 py-1 rounded hover:border-accent/30 transition-colors flex items-center gap-1">
                    View <ArrowRight size={10} />
                  </Link>
                  <button onClick={() => handleDelete(run.run_id)} disabled={deleting === run.run_id}
                    className="text-xs text-muted hover:text-accent5 transition-colors p-1 rounded hover:bg-accent5/10 disabled:opacity-50">
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
