'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Play, Clock, CheckCircle, XCircle, Brain, Zap, ArrowRight, TrendingUp } from 'lucide-react'

const STAGE_LABELS = ['Init', 'Keywords', 'SERP', 'Outline', 'Content', 'On-Page', 'Links', 'Memory']

function StatCard({ label, value, sub, color = 'accent', icon: Icon }) {
  const colorMap = { accent: 'text-accent border-accent/20 bg-accent/5', accent3: 'text-accent3 border-accent3/20 bg-accent3/5', accent4: 'text-accent4 border-accent4/20 bg-accent4/5', accent5: 'text-accent5 border-accent5/20 bg-accent5/5' }
  return (
    <div className={`border rounded p-5 ${colorMap[color]}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="text-xs text-muted uppercase tracking-widest">{label}</div>
        {Icon && <Icon size={14} className="opacity-60" />}
      </div>
      <div className="text-3xl font-sans font-bold mb-1">{value}</div>
      <div className="text-xs text-muted">{sub}</div>
    </div>
  )
}

function RunRow({ run }) {
  const statusColor = { done: 'text-accent3', running: 'text-accent', failed: 'text-accent5', pending: 'text-muted' }
  const statusDot = { done: 'bg-accent3', running: 'bg-accent animate-pulse', failed: 'bg-accent5', pending: 'bg-dim' }
  const completedStages = Object.values(run.stages || {}).filter(s => s === 'done').length
  const totalStages = Object.keys(run.stages || {}).length || 7
  const pct = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0

  return (
    <Link href={`/runs/${run.run_id}`} className="flex items-center gap-4 px-4 py-3 hover:bg-surface2 border-b border-border/50 transition-colors group">
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[run.status] || 'bg-dim'}`} />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-white truncate">{run.task}</div>
        <div className="text-xs text-muted mt-0.5">{run.run_id}</div>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-24 h-1 bg-dim rounded-full overflow-hidden">
          <div className="h-full bg-accent3 rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-xs text-muted w-8 text-right">{pct}%</span>
        <span className={`text-xs font-mono w-16 text-right ${statusColor[run.status] || 'text-muted'}`}>{run.status}</span>
        <ArrowRight size={12} className="text-dim group-hover:text-muted transition-colors" />
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [memory, setMemory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/runs').then(r => r.json()).catch(() => ({ runs: [] })),
      fetch('/api/memory').then(r => r.json()).catch(() => ({ learnings: [] }))
    ]).then(([runsData, memData]) => {
      setRuns(runsData.runs || [])
      setMemory(memData.learnings || [])
      setLoading(false)
    })
  }, [])

  const stats = {
    total: runs.length,
    done: runs.filter(r => r.status === 'done').length,
    failed: runs.filter(r => r.status === 'failed').length,
    running: runs.filter(r => r.status === 'running').length,
  }

  const recentRuns = [...runs].sort((a, b) => b.run_id.localeCompare(a.run_id)).slice(0, 8)

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
            <Zap size={10} className="text-accent" />
            Autonomous SEO Pipeline
          </div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-muted text-xs mt-1">Monitor runs · Review outputs · Track learnings</p>
        </div>
        <Link href="/task"
          className="flex items-center gap-2 px-4 py-2.5 bg-accent text-bg text-xs font-bold rounded tracking-wide hover:bg-accent/90 transition-colors">
          <Play size={12} />
          NEW RUN
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Runs" value={loading ? '—' : stats.total} sub="all time" color="accent" icon={TrendingUp} />
        <StatCard label="Completed" value={loading ? '—' : stats.done} sub="successful" color="accent3" icon={CheckCircle} />
        <StatCard label="Active" value={loading ? '—' : stats.running} sub="in progress" color="accent4" icon={Clock} />
        <StatCard label="Failed" value={loading ? '—' : stats.failed} sub="need attention" color="accent5" icon={XCircle} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent Runs */}
        <div className="col-span-2 bg-surface border border-border rounded overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface2">
            <span className="text-xs font-bold text-white tracking-wide">RECENT RUNS</span>
            <Link href="/runs" className="text-xs text-muted hover:text-accent transition-colors flex items-center gap-1">
              View all <ArrowRight size={10} />
            </Link>
          </div>
          {loading ? (
            <div className="p-8 text-center text-xs text-muted">Loading...</div>
          ) : recentRuns.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-xs text-muted mb-3">No runs yet</div>
              <Link href="/task" className="text-xs text-accent hover:underline">Start your first run →</Link>
            </div>
          ) : (
            recentRuns.map(run => <RunRow key={run.run_id} run={run} />)
          )}
        </div>

        {/* Memory Highlights */}
        <div className="bg-surface border border-border rounded overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface2">
            <div className="flex items-center gap-2">
              <Brain size={12} className="text-accent3" />
              <span className="text-xs font-bold text-white tracking-wide">LEARNINGS</span>
            </div>
            <Link href="/memory" className="text-xs text-muted hover:text-accent3 transition-colors">
              <ArrowRight size={10} />
            </Link>
          </div>
          <div className="p-4 space-y-3">
            {loading ? (
              <div className="text-xs text-muted">Loading...</div>
            ) : memory.length === 0 ? (
              <div className="text-xs text-muted">No learnings yet. Complete a run to generate insights.</div>
            ) : (
              memory.slice(0, 5).map((item, i) => (
                <div key={i} className="border border-border/50 rounded p-3 bg-surface2/50">
                  <div className="text-xs text-white truncate mb-1">{item.task}</div>
                  <div className="text-xs text-muted">
                    {item.insights?.slice(0, 1).map((ins, j) => (
                      <div key={j} className="flex items-start gap-1.5">
                        <span className="text-accent3 mt-0.5">›</span>
                        <span>{ins}</span>
                      </div>
                    ))}
                  </div>
                  {item.ranking && (
                    <div className="mt-2 text-xs">
                      <span className="text-muted">Rank: </span>
                      <span className="text-accent4">#{item.ranking}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
