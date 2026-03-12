'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Play, ChevronRight, Info, Zap } from 'lucide-react'

const WORKFLOW_STEPS = [
  { n: '01', label: 'Keyword Research', desc: 'Find primary + secondary keywords, search intent' },
  { n: '02', label: 'SERP Analysis', desc: 'Analyze top 10, identify content gaps' },
  { n: '03', label: 'Content Outline', desc: 'H1/H2 structure, FAQ, meta tags' },
  { n: '04', label: 'Content Writing', desc: 'Full SEO-optimized article generation' },
  { n: '05', label: 'On-Page Optimization', desc: 'KW density, schema, entity check, score' },
  { n: '06', label: 'Internal Linking', desc: 'Topic cluster, anchor text map' },
]

export default function TaskPage() {
  const router = useRouter()
  const [form, setForm] = useState({
    task: '',
    target: '',
    audience: '',
    domain: '',
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.task.trim()) return
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to start run')
      router.push(`/runs/${data.run_id}`)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
          <Zap size={10} className="text-accent" /> New Agent Run
        </div>
        <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Create Task</h1>
        <p className="text-muted text-xs mt-1">The manager agent will plan and dispatch the pipeline automatically</p>
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Form */}
        <div className="col-span-3">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Main Task */}
            <div className="bg-surface border border-border rounded p-5">
              <label className="block text-xs text-muted uppercase tracking-widest mb-3">
                Target Keyword / Topic *
              </label>
              <input
                type="text"
                value={form.task}
                onChange={e => setForm(f => ({ ...f, task: e.target.value }))}
                placeholder="e.g. crypto exchange development cost"
                className="w-full bg-surface2 border border-border rounded px-4 py-3 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors"
                required
              />
              <div className="mt-2 text-xs text-muted flex items-center gap-1.5">
                <Info size={10} />
                This becomes the primary keyword for the entire pipeline
              </div>
            </div>

            {/* Target + Audience */}
            <div className="bg-surface border border-border rounded p-5 space-y-4">
              <div>
                <label className="block text-xs text-muted uppercase tracking-widest mb-2">Target Market</label>
                <input
                  type="text"
                  value={form.target}
                  onChange={e => setForm(f => ({ ...f, target: e.target.value }))}
                  placeholder="e.g. United States, UK, Global"
                  className="w-full bg-surface2 border border-border rounded px-4 py-2.5 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-muted uppercase tracking-widest mb-2">Target Audience</label>
                <input
                  type="text"
                  value={form.audience}
                  onChange={e => setForm(f => ({ ...f, audience: e.target.value }))}
                  placeholder="e.g. B2B founders, startup CTOs, enterprise buyers"
                  className="w-full bg-surface2 border border-border rounded px-4 py-2.5 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-muted uppercase tracking-widest mb-2">Domain / Website</label>
                <input
                  type="text"
                  value={form.domain}
                  onChange={e => setForm(f => ({ ...f, domain: e.target.value }))}
                  placeholder="e.g. yoursite.com (for internal linking context)"
                  className="w-full bg-surface2 border border-border rounded px-4 py-2.5 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors"
                />
              </div>
            </div>

            {/* Notes */}
            <div className="bg-surface border border-border rounded p-5">
              <label className="block text-xs text-muted uppercase tracking-widest mb-2">Additional Notes</label>
              <textarea
                value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                placeholder="Any specific angle, competitors to beat, content format requirements..."
                rows={3}
                className="w-full bg-surface2 border border-border rounded px-4 py-3 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors resize-none"
              />
            </div>

            {error && (
              <div className="bg-accent5/10 border border-accent5/30 rounded px-4 py-3 text-xs text-accent5">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !form.task.trim()}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-accent text-bg text-xs font-bold rounded tracking-wide hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? (
                <>
                  <span className="w-3 h-3 border border-bg border-t-transparent rounded-full animate-spin" />
                  STARTING PIPELINE...
                </>
              ) : (
                <>
                  <Play size={12} />
                  LAUNCH AGENT RUN
                </>
              )}
            </button>
          </form>
        </div>

        {/* Pipeline Preview */}
        <div className="col-span-2">
          <div className="bg-surface border border-border rounded overflow-hidden">
            <div className="px-4 py-3 border-b border-border bg-surface2 text-xs font-bold text-white tracking-wide">
              PIPELINE STAGES
            </div>
            <div className="p-4 space-y-2">
              {WORKFLOW_STEPS.map((step, i) => (
                <div key={i} className="flex items-start gap-3 group">
                  <div className="flex flex-col items-center">
                    <div className="w-6 h-6 rounded border border-dim text-xs text-muted flex items-center justify-center flex-shrink-0 font-mono">
                      {step.n}
                    </div>
                    {i < WORKFLOW_STEPS.length - 1 && (
                      <div className="w-px h-4 bg-dim mt-1" />
                    )}
                  </div>
                  <div className="pb-2">
                    <div className="text-xs text-white">{step.label}</div>
                    <div className="text-xs text-muted mt-0.5">{step.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 bg-accent3/5 border border-accent3/20 rounded p-4">
            <div className="text-xs text-accent3 font-bold mb-2 flex items-center gap-1.5">
              <Info size={11} /> SMART CACHING
            </div>
            <div className="text-xs text-muted leading-relaxed">
              Each stage output is saved as JSON. If a run fails, resume picks up from the last completed stage — no API tokens wasted.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
