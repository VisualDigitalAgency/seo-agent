'use client'
import { useEffect, useState } from 'react'
import { CalendarClock, Plus, Trash2, Play, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const FREQ_OPTIONS = [
  { value: 'hourly',  label: 'Every hour' },
  { value: 'daily',   label: 'Daily' },
  { value: 'weekly',  label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'custom',  label: 'Custom cron' },
]

const DOW   = ['mon','tue','wed','thu','fri','sat','sun']
const HOURS = Array.from({length: 24}, (_, i) => i)

const inputStyle = { width: '100%', padding: '10px 12px', background: 'white', border: '1px solid #E5E5E0', borderRadius: 8, fontSize: 13, color: '#0A0A0A', fontFamily: 'Plus Jakarta Sans, sans-serif', outline: 'none' }

const FREQ_COLOR = { hourly: '#0041FF', daily: '#059669', weekly: '#D97706', monthly: '#7C3AED', custom: '#DC2626' }

function ScheduleCard({ sched, onDelete, onRunNow }) {
  const [deleting, setDeleting] = useState(false)
  const [running, setRunning]   = useState(false)
  const fc = FREQ_COLOR[sched.frequency] || '#8A8A82'

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#0A0A0A', marginBottom: 3 }}>{sched.name}</div>
          <div style={{ fontSize: 12, color: '#8A8A82' }}>{sched.task_config?.task}</div>
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 20, background: fc + '15', color: fc, border: `1px solid ${fc}30` }}>
          {FREQ_OPTIONS.find(f => f.value === sched.frequency)?.label || sched.frequency}
        </span>
      </div>
      <div className="grid-2col" style={{ marginBottom: 14 }}>
        {[
          { label: 'Next run',  value: sched.next_run ? new Date(sched.next_run).toLocaleString() : '—' },
          { label: 'Last run',  value: sched.last_run ? new Date(sched.last_run).toLocaleString() : 'Never' },
          { label: 'Run count', value: sched.run_count || 0 },
          { label: 'Target',    value: sched.task_config?.target || 'Global' },
        ].map(s => (
          <div key={s.label} style={{ background: '#FAFAF8', border: '1px solid #E5E5E0', borderRadius: 8, padding: '10px 12px' }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 12, color: '#0A0A0A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={async () => { setRunning(true); await onRunNow(sched.id); setRunning(false) }} disabled={running}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '1px solid #0041FF', borderRadius: 7, background: '#EEF1FF', color: '#0041FF', fontSize: 12, fontWeight: 600, cursor: 'pointer', opacity: running ? 0.6 : 1 }}>
          {running ? <RefreshCw size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Play size={11} />}
          Run Now
        </button>
        <button onClick={async () => { setDeleting(true); await onDelete(sched.id) }} disabled={deleting}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '1px solid #FECACA', borderRadius: 7, background: '#FEF2F2', color: '#DC2626', fontSize: 12, fontWeight: 600, cursor: 'pointer', marginLeft: 'auto', opacity: deleting ? 0.6 : 1 }}>
          {deleting ? <RefreshCw size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Trash2 size={11} />}
          Delete
        </button>
      </div>
    </div>
  )
}

function NewScheduleForm({ onCreated }) {
  const [form, setForm] = useState({ name: '', frequency: 'weekly', hour: 9, minute: 0, day_of_week: 'mon', day_of_month: 1, cron_expr: '', task: '', target: '', audience: '', domain: '', notes: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.task.trim()) { setError('Task keyword is required'); return }
    setSaving(true); setError(null)
    try {
      const postRes = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name || form.task, frequency: form.frequency, hour: form.hour, minute: form.minute,
          day_of_week: form.day_of_week, day_of_month: form.day_of_month, cron_expr: form.cron_expr,
          task_config: { task: form.task, target: form.target, audience: form.audience, domain: form.domain, notes: form.notes },
        }),
      })
      if (!postRes.ok) {
        const err = await postRes.json().catch(() => ({ error: postRes.statusText }))
        throw new Error(err.error || 'Failed to create schedule')
      }
      onCreated()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const selectStyle = { ...inputStyle, appearance: 'none' }

  return (
    <div className="card" style={{ padding: 24, marginBottom: 24 }}>
      <div style={{ ...syne, fontSize: 14, fontWeight: 700, color: '#0A0A0A', marginBottom: 20 }}>New Schedule</div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="grid-2col">
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>Schedule Name</div>
            <input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Weekly Crypto Blog" style={inputStyle}
              onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
              onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }} />
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>Frequency</div>
            <select value={form.frequency} onChange={e => set('frequency', e.target.value)} style={selectStyle}>
              {FREQ_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </div>
        </div>

        {form.frequency !== 'hourly' && form.frequency !== 'custom' && (
          <div className="grid-3col" style={{ gap: 12 }}>
            {form.frequency === 'weekly' && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Day of Week</div>
                <select value={form.day_of_week} onChange={e => set('day_of_week', e.target.value)} style={selectStyle}>
                  {DOW.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
                </select>
              </div>
            )}
            {form.frequency === 'monthly' && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Day of Month</div>
                <input type="number" min="1" max="28" value={form.day_of_month} onChange={e => set('day_of_month', parseInt(e.target.value))} style={inputStyle} />
              </div>
            )}
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Hour (UTC)</div>
              <select value={form.hour} onChange={e => set('hour', parseInt(e.target.value))} style={selectStyle}>
                {HOURS.map(h => <option key={h} value={h}>{String(h).padStart(2,'0')}:00</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Minute</div>
              <select value={form.minute} onChange={e => set('minute', parseInt(e.target.value))} style={selectStyle}>
                {[0,15,30,45].map(m => <option key={m} value={m}>{String(m).padStart(2,'0')}</option>)}
              </select>
            </div>
          </div>
        )}
        {form.frequency === 'custom' && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Cron Expression</div>
            <input value={form.cron_expr} onChange={e => set('cron_expr', e.target.value)} placeholder="0 9 * * 1  (every Monday at 9am UTC)" style={{ ...inputStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </div>
        )}

        <div style={{ borderTop: '1px solid #E5E5E0', paddingTop: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Task Configuration</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input value={form.task} onChange={e => set('task', e.target.value)} placeholder="Target keyword / topic *" required style={inputStyle}
              onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
              onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }} />
            <div className="grid-2col" style={{ gap: 10 }}>
              <input value={form.target} onChange={e => set('target', e.target.value)} placeholder="Target market (e.g. US)" style={inputStyle} />
              <input value={form.audience} onChange={e => set('audience', e.target.value)} placeholder="Target audience" style={inputStyle} />
            </div>
            <input value={form.domain} onChange={e => set('domain', e.target.value)} placeholder="Domain (yoursite.com)" style={inputStyle} />
          </div>
        </div>

        {error && <div style={{ fontSize: 12, color: '#DC2626', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 7, padding: '10px 12px' }}>{error}</div>}

        <button type="submit" disabled={saving} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          padding: '12px 24px', background: '#0041FF', color: 'white',
          border: 'none', borderRadius: 8, cursor: saving ? 'not-allowed' : 'pointer',
          ...syne, fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
          opacity: saving ? 0.7 : 1,
        }}>
          {saving ? <RefreshCw size={12} style={{ animation: 'spin 0.7s linear infinite' }} /> : <Plus size={12} />}
          Create Schedule
        </button>
      </form>
    </div>
  )
}

export default function SchedulerPage() {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [toast, setToast]         = useState(null)

  const fetchSchedules = async () => {
    try {
      const res  = await fetch('/api/schedule', { cache: 'no-store' })
      const data = await res.json()
      setSchedules(data.schedules || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchSchedules() }, [])

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000) }

  const handleDelete = async (id) => {
    await fetch(`/api/schedule/${id}`, { method: 'DELETE' })
    showToast('Schedule deleted'); fetchSchedules()
  }

  const handleRunNow = async (id) => {
    const res  = await fetch(`/api/schedule/${id}?action=run-now`, { method: 'POST' })
    const data = await res.json()
    showToast(`Run started: ${data.run_id}`)
    window.location.href = `/runs/${data.run_id}`
  }

  return (
    <div className="animate-fade-in">
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 1000,
          padding: '12px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          background: toast.type === 'error' ? '#FEF2F2' : '#ECFDF5',
          border: `1px solid ${toast.type === 'error' ? '#FECACA' : '#A7F3D0'}`,
          color: toast.type === 'error' ? '#DC2626' : '#059669',
          boxShadow: '0 4px 16px rgba(0,0,0,0.10)',
        }}>
          {toast.msg}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Automation</div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', marginBottom: 4 }}>Scheduler</h1>
          <p style={{ fontSize: 13, color: '#8A8A82' }}>Automate recurring SEO runs — daily, weekly, monthly, or custom cron</p>
        </div>
        <button onClick={() => setShowForm(s => !s)} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '11px 20px',
          background: showForm ? '#F3F3EF' : '#0041FF',
          color: showForm ? '#3D3D38' : 'white',
          border: showForm ? '1px solid #E5E5E0' : 'none', borderRadius: 8, cursor: 'pointer',
          ...syne, fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>
          {showForm ? <ChevronUp size={12} /> : <Plus size={12} />}
          {showForm ? 'Cancel' : 'New Schedule'}
        </button>
      </div>

      {showForm && <NewScheduleForm onCreated={() => { setShowForm(false); fetchSchedules(); showToast('Schedule created!') }} />}

      {loading ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#8A8A82', fontSize: 13 }}>Loading schedules…</div>
      ) : schedules.length === 0 ? (
        <div className="card" style={{ padding: 72, textAlign: 'center' }}>
          <CalendarClock size={36} style={{ color: '#E5E5E0', margin: '0 auto 16px' }} />
          <div style={{ fontSize: 14, color: '#8A8A82', marginBottom: 12 }}>No schedules yet</div>
          <button onClick={() => setShowForm(true)} style={{ fontSize: 13, color: '#0041FF', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 500 }}>
            Create your first schedule →
          </button>
        </div>
      ) : (
        <div className="grid-2col">
          {schedules.map(s => (
            <ScheduleCard key={s.id} sched={s} onDelete={handleDelete} onRunNow={handleRunNow} />
          ))}
        </div>
      )}
    </div>
  )
}
