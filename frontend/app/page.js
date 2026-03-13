'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Play, CheckCircle, XCircle, Clock, ArrowRight, TrendingUp, Zap, Brain } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

function StatusDot({ status }) {
  const map = {
    done:    { bg: '#059669' },
    running: { bg: '#0041FF', pulse: true },
    failed:  { bg: '#DC2626' },
    pending: { bg: '#C8C8C0' },
  }
  const s = map[status] || map.pending
  return (
    <span
      style={{ width: 8, height: 8, borderRadius: '50%', background: s.bg, display: 'inline-block', flexShrink: 0 }}
      className={s.pulse ? 'animate-pulse' : ''}
    />
  )
}

function StatCard({ label, value, icon: Icon, color = '#0041FF' }) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <span style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{label}</span>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: color + '12', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={14} style={{ color }} />
        </div>
      </div>
      <div style={{ ...syne, fontSize: 40, fontWeight: 700, color: '#0A0A0A', lineHeight: 1 }}>
        {value}
      </div>
    </div>
  )
}

function RunRow({ run }) {
  const statusLabel = { done: 'Done', running: 'Running', failed: 'Failed', pending: 'Pending' }
  const statusColor = { done: '#059669', running: '#0041FF', failed: '#DC2626', pending: '#8A8A82' }
  const statusBg    = { done: '#ECFDF5', running: '#EEF1FF', failed: '#FEF2F2', pending: '#F3F3EF' }
  const completed = Object.values(run.stages || {}).filter(s => s === 'done').length
  const total     = Object.keys(run.stages || {}).length || 7
  const pct       = Math.round((completed / total) * 100)

  return (
    <Link
      href={`/runs/${run.run_id}`}
      style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 20px', borderBottom: '1px solid #E5E5E0', textDecoration: 'none', transition: 'background 0.1s' }}
      onMouseEnter={e => e.currentTarget.style.background = '#FAFAF8'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <StatusDot status={run.status} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: '#0A0A0A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{run.task}</div>
        <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>{run.run_id}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 80, height: 3, background: '#E5E5E0', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: '#0041FF', borderRadius: 4, transition: 'width 0.3s' }} />
          </div>
          <span style={{ fontSize: 11, color: '#8A8A82', minWidth: 28 }}>{pct}%</span>
        </div>
        <span style={{
          fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 20,
          background: statusBg[run.status] || statusBg.pending,
          color: statusColor[run.status] || statusColor.pending,
        }}>
          {statusLabel[run.status] || run.status}
        </span>
        <ArrowRight size={13} style={{ color: '#C8C8C0' }} />
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const [runs, setRuns]     = useState([])
  const [memory, setMemory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/runs').then(r => r.json()).catch(() => ({ runs: [] })),
      fetch('/api/memory').then(r => r.json()).catch(() => ({ learnings: [] }))
    ]).then(([r, m]) => {
      setRuns(r.runs || [])
      setMemory(m.learnings || [])
      setLoading(false)
    })
  }, [])

  const stats = {
    total:   runs.length,
    done:    runs.filter(r => r.status === 'done').length,
    running: runs.filter(r => r.status === 'running').length,
    failed:  runs.filter(r => r.status === 'failed').length,
  }
  const recent = [...runs].sort((a, b) => b.run_id.localeCompare(a.run_id)).slice(0, 8)

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-10">
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>
            Autonomous SEO Pipeline
          </div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', lineHeight: 1.1, letterSpacing: '-0.5px' }}>
            Dashboard
          </h1>
          <p style={{ fontSize: 13, color: '#8A8A82', marginTop: 6 }}>
            Monitor runs · Review outputs · Track learnings
          </p>
        </div>
        <Link
          href="/task"
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '11px 20px',
            background: '#0041FF', color: '#FFFFFF',
            fontFamily: 'Syne, sans-serif', fontSize: 12, fontWeight: 700,
            letterSpacing: '0.06em', textTransform: 'uppercase',
            borderRadius: 8, textDecoration: 'none',
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.88'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          <Play size={12} />
          New Run
        </Link>
      </div>

      {/* Stats */}
      <div className="grid-stats mb-10">
        <StatCard label="Total Runs"  value={loading ? '—' : stats.total}   icon={TrendingUp} color="#0041FF" />
        <StatCard label="Completed"   value={loading ? '—' : stats.done}    icon={CheckCircle} color="#059669" />
        <StatCard label="Active"      value={loading ? '—' : stats.running} icon={Zap}         color="#D97706" />
        <StatCard label="Failed"      value={loading ? '—' : stats.failed}  icon={XCircle}     color="#DC2626" />
      </div>

      <div className="grid-dash">
        {/* Recent Runs */}
        <div className="card overflow-hidden">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #E5E5E0' }}>
            <span style={{ ...syne, fontSize: 12, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Recent Runs</span>
            <Link href="/runs" style={{ fontSize: 12, color: '#8A8A82', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
              onMouseEnter={e => e.currentTarget.style.color = '#0041FF'}
              onMouseLeave={e => e.currentTarget.style.color = '#8A8A82'}>
              View all <ArrowRight size={11} />
            </Link>
          </div>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#8A8A82', fontSize: 13 }}>Loading…</div>
          ) : recent.length === 0 ? (
            <div style={{ padding: 48, textAlign: 'center' }}>
              <div style={{ fontSize: 13, color: '#8A8A82', marginBottom: 12 }}>No runs yet</div>
              <Link href="/task" style={{ fontSize: 13, color: '#0041FF', textDecoration: 'none', fontWeight: 500 }}>
                Start your first run →
              </Link>
            </div>
          ) : (
            recent.map(run => <RunRow key={run.run_id} run={run} />)
          )}
        </div>

        {/* Memory */}
        <div className="card overflow-hidden">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #E5E5E0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Brain size={13} style={{ color: '#059669' }} />
              <span style={{ ...syne, fontSize: 12, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Learnings</span>
            </div>
            <Link href="/memory" style={{ color: '#C8C8C0', textDecoration: 'none' }}>
              <ArrowRight size={12} />
            </Link>
          </div>
          <div style={{ padding: '12px 16px' }}>
            {loading ? (
              <div style={{ fontSize: 13, color: '#8A8A82' }}>Loading…</div>
            ) : memory.length === 0 ? (
              <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: '#8A8A82' }}>
                No learnings yet.<br />Complete a run to generate insights.
              </div>
            ) : memory.slice(0, 5).map((item, i) => (
              <div key={i} style={{ padding: '10px 0', borderBottom: i < 4 ? '1px solid #F3F3EF' : 'none' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.task}</div>
                {item.insights?.slice(0, 1).map((ins, j) => (
                  <div key={j} style={{ display: 'flex', gap: 6, fontSize: 11, color: '#8A8A82' }}>
                    <span style={{ color: '#059669', flexShrink: 0 }}>›</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ins}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
