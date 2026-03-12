'use client'
import { useEffect, useState } from 'react'
import { CalendarClock, Plus, Trash2, Play, Clock, CheckCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { apiGet, apiPost, apiDelete } from '@/lib/api'

const FREQ_OPTIONS = [
  { value: 'hourly',  label: 'Every hour' },
  { value: 'daily',   label: 'Daily' },
  { value: 'weekly',  label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'custom',  label: 'Custom cron' },
]

const DOW = ['mon','tue','wed','thu','fri','sat','sun']
const HOURS = Array.from({length: 24}, (_, i) => i)

function ScheduleCard({ sched, onDelete, onRunNow }) {
  const [deleting, setDeleting] = useState(false)
  const [running, setRunning]   = useState(false)

  const freqColor = {
    hourly: 'text-accent', daily: 'text-accent3', weekly: 'text-accent4',
    monthly: 'text-purple-400', custom: 'text-pink-400',
  }

  return (
    <div className="bg-surface border border-border rounded p-5 hover:border-accent/20 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-bold text-white">{sched.name}</div>
          <div className="text-xs text-muted mt-0.5">{sched.task_config?.task}</div>
        </div>
        <span className={`text-xs px-2 py-1 rounded border bg-surface2 ${freqColor[sched.frequency] || 'text-muted'} border-current/20`}>
          {FREQ_OPTIONS.find(f => f.value === sched.frequency)?.label || sched.frequency}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
        <div className="bg-surface2 rounded p-2.5">
          <div className="text-muted mb-1">Next run</div>
          <div className="text-white">{sched.next_run ? new Date(sched.next_run).toLocaleString() : '—'}</div>
        </div>
        <div className="bg-surface2 rounded p-2.5">
          <div className="text-muted mb-1">Last run</div>
          <div className="text-white">{sched.last_run ? new Date(sched.last_run).toLocaleString() : 'Never'}</div>
        </div>
        <div className="bg-surface2 rounded p-2.5">
          <div className="text-muted mb-1">Run count</div>
          <div className="text-white">{sched.run_count || 0}</div>
        </div>
        <div className="bg-surface2 rounded p-2.5">
          <div className="text-muted mb-1">Target</div>
          <div className="text-white truncate">{sched.task_config?.target || 'Global'}</div>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={async () => { setRunning(true); await onRunNow(sched.id); setRunning(false) }}
          disabled={running}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-accent4 border border-accent4/30 rounded hover:bg-accent4/10 transition-colors disabled:opacity-50">
          {running ? <RefreshCw size={11} className="animate-spin" /> : <Play size={11} />}
          Run Now
        </button>
        <button onClick={async () => { setDeleting(true); await onDelete(sched.id) }}
          disabled={deleting}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-accent5 border border-accent5/30 rounded hover:bg-accent5/10 transition-colors disabled:opacity-50 ml-auto">
          {deleting ? <RefreshCw size={11} className="animate-spin" /> : <Trash2 size={11} />}
          Delete
        </button>
      </div>
    </div>
  )
}

function NewScheduleForm({ onCreated }) {
  const [form, setForm] = useState({
    name: '', frequency: 'weekly', hour: 9, minute: 0,
    day_of_week: 'mon', day_of_month: 1, cron_expr: '',
    task: '', target: '', audience: '', domain: '', notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.task.trim()) { setError('Task keyword is required'); return }
    setSaving(true); setError(null)
    try {
      await apiPost('/schedules', {
        name: form.name || form.task,
        frequency:    form.frequency,
        hour:         form.hour,
        minute:       form.minute,
        day_of_week:  form.day_of_week,
        day_of_month: form.day_of_month,
        cron_expr:    form.cron_expr,
        task_config:  { task: form.task, target: form.target, audience: form.audience, domain: form.domain, notes: form.notes },
      })
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-border rounded p-6 space-y-5">
      <div className="text-xs font-bold text-white uppercase tracking-widest mb-2">New Schedule</div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-muted mb-1.5">Schedule Name</label>
          <input value={form.name} onChange={e => set('name', e.target.value)}
            placeholder="e.g. Weekly Crypto Blog"
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white placeholder-muted focus:outline-none focus:border-accent" />
        </div>
        <div>
          <label className="block text-xs text-muted mb-1.5">Frequency</label>
          <select value={form.frequency} onChange={e => set('frequency', e.target.value)}
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent">
            {FREQ_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </div>
      </div>

      {/* Timing options */}
      {form.frequency !== 'hourly' && form.frequency !== 'custom' && (
        <div className="grid grid-cols-3 gap-3">
          {form.frequency === 'weekly' && (
            <div>
              <label className="block text-xs text-muted mb-1.5">Day of Week</label>
              <select value={form.day_of_week} onChange={e => set('day_of_week', e.target.value)}
                className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent">
                {DOW.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
              </select>
            </div>
          )}
          {form.frequency === 'monthly' && (
            <div>
              <label className="block text-xs text-muted mb-1.5">Day of Month</label>
              <input type="number" min="1" max="28" value={form.day_of_month}
                onChange={e => set('day_of_month', parseInt(e.target.value))}
                className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent" />
            </div>
          )}
          <div>
            <label className="block text-xs text-muted mb-1.5">Hour (UTC)</label>
            <select value={form.hour} onChange={e => set('hour', parseInt(e.target.value))}
              className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent">
              {HOURS.map(h => <option key={h} value={h}>{String(h).padStart(2,'0')}:00</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-muted mb-1.5">Minute</label>
            <select value={form.minute} onChange={e => set('minute', parseInt(e.target.value))}
              className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent">
              {[0,15,30,45].map(m => <option key={m} value={m}>{String(m).padStart(2,'0')}</option>)}
            </select>
          </div>
        </div>
      )}
      {form.frequency === 'custom' && (
        <div>
          <label className="block text-xs text-muted mb-1.5">Cron Expression <span className="text-dim">(min hour day month dow)</span></label>
          <input value={form.cron_expr} onChange={e => set('cron_expr', e.target.value)}
            placeholder="0 9 * * 1  (every Monday at 9am UTC)"
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white font-mono placeholder-muted focus:outline-none focus:border-accent" />
        </div>
      )}

      {/* Task config */}
      <div className="border-t border-border pt-4 space-y-3">
        <div className="text-xs text-muted uppercase tracking-widest">Task Configuration</div>
        <input value={form.task} onChange={e => set('task', e.target.value)}
          placeholder="Target keyword / topic *"
          className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white placeholder-muted focus:outline-none focus:border-accent" required />
        <div className="grid grid-cols-2 gap-3">
          <input value={form.target} onChange={e => set('target', e.target.value)}
            placeholder="Target market (e.g. US)"
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white placeholder-muted focus:outline-none focus:border-accent" />
          <input value={form.audience} onChange={e => set('audience', e.target.value)}
            placeholder="Target audience"
            className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white placeholder-muted focus:outline-none focus:border-accent" />
        </div>
        <input value={form.domain} onChange={e => set('domain', e.target.value)}
          placeholder="Domain (yoursite.com)"
          className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white placeholder-muted focus:outline-none focus:border-accent" />
      </div>

      {error && <div className="text-xs text-accent5 bg-accent5/10 border border-accent5/30 rounded px-3 py-2">{error}</div>}

      <button type="submit" disabled={saving}
        className="w-full flex items-center justify-center gap-2 py-2.5 bg-accent text-bg text-xs font-bold rounded hover:bg-accent/90 transition-colors disabled:opacity-50">
        {saving ? <RefreshCw size={12} className="animate-spin" /> : <Plus size={12} />}
        CREATE SCHEDULE
      </button>
    </form>
  )
}

export default function SchedulerPage() {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [toast, setToast]         = useState(null)

  const fetchSchedules = async () => {
    try {
      const data = await apiGet('/schedules')
      setSchedules(data.schedules || [])
    } catch { }
    setLoading(false)
  }

  useEffect(() => { fetchSchedules() }, [])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleDelete = async (id) => {
    await apiDelete(`/schedules/${id}`)
    showToast('Schedule deleted')
    fetchSchedules()
  }

  const handleRunNow = async (id) => {
    const data = await apiPost(`/schedules/${id}/run-now`)
    showToast(`Run started: ${data.run_id}`)
    window.location.href = `/runs/${data.run_id}`
  }

  return (
    <div className="animate-fade-in">
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded border text-xs font-bold
          ${toast.type === 'error' ? 'bg-accent5/10 border-accent5/30 text-accent5' : 'bg-accent3/10 border-accent3/30 text-accent3'}`}>
          {toast.msg}
        </div>
      )}

      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
            <CalendarClock size={10} className="text-accent4" /> Automation
          </div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Scheduler</h1>
          <p className="text-muted text-xs mt-1">Automate recurring SEO runs — daily, weekly, monthly, or custom cron</p>
        </div>
        <button onClick={() => setShowForm(s => !s)}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent text-bg text-xs font-bold rounded hover:bg-accent/90 transition-colors">
          {showForm ? <ChevronUp size={12} /> : <Plus size={12} />}
          {showForm ? 'CANCEL' : 'NEW SCHEDULE'}
        </button>
      </div>

      {showForm && (
        <div className="mb-8">
          <NewScheduleForm onCreated={() => { setShowForm(false); fetchSchedules(); showToast('Schedule created!') }} />
        </div>
      )}

      {loading ? (
        <div className="text-xs text-muted p-8 text-center">Loading schedules...</div>
      ) : schedules.length === 0 ? (
        <div className="bg-surface border border-border rounded p-12 text-center">
          <CalendarClock size={32} className="text-dim mx-auto mb-3" />
          <div className="text-xs text-muted mb-2">No schedules yet</div>
          <button onClick={() => setShowForm(true)} className="text-xs text-accent hover:underline">Create your first schedule →</button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {schedules.map(s => (
            <ScheduleCard key={s.id} sched={s} onDelete={handleDelete} onRunNow={handleRunNow} />
          ))}
        </div>
      )}
    </div>
  )
}
