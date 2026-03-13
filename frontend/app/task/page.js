'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Play, Info } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const STAGES = [
  { n: '01', label: 'Keyword Research',     desc: 'Primary & secondary keywords, search intent' },
  { n: '02', label: 'SERP Analysis',        desc: 'Top 10 analysis, content gap mapping' },
  { n: '03', label: 'Content Outline',      desc: 'H1/H2 structure, FAQ, meta tags' },
  { n: '04', label: 'Content Writing',      desc: 'Full SEO-optimized article generation' },
  { n: '05', label: 'On-Page Optimization', desc: 'KW density, schema, entity check, score' },
  { n: '06', label: 'Internal Linking',     desc: 'Topic cluster, anchor text map' },
]

function Label({ children }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
      {children}
    </div>
  )
}

function Input({ value, onChange, placeholder, required }) {
  return (
    <input
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      style={{
        width: '100%', padding: '11px 14px',
        background: 'white', border: '1px solid #E5E5E0',
        borderRadius: 8, fontSize: 14, color: '#0A0A0A',
        fontFamily: 'Plus Jakarta Sans, sans-serif',
        outline: 'none', transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
      onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
      onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }}
    />
  )
}

export default function TaskPage() {
  const router = useRouter()
  const [form, setForm] = useState({ task: '', target: '', audience: '', domain: '', notes: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.task.trim()) return
    setLoading(true); setError(null)
    try {
      const res  = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to start run')
      router.push(`/runs/${data.run_id}`)
    } catch (err) {
      setError(err.message); setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>
          New Agent Run
        </div>
        <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', lineHeight: 1.1 }}>
          Create Task
        </h1>
        <p style={{ fontSize: 13, color: '#8A8A82', marginTop: 6 }}>
          The manager agent will plan and dispatch the pipeline automatically
        </p>
      </div>

      <div className="grid-task-preview">
        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Main task */}
          <div className="card" style={{ padding: 24 }}>
            <Label>Target Keyword / Topic *</Label>
            <Input
              value={form.task}
              onChange={set('task')}
              placeholder="e.g. crypto exchange development cost"
              required
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, fontSize: 11, color: '#8A8A82' }}>
              <Info size={10} />
              This becomes the primary keyword for the entire pipeline
            </div>
          </div>

          {/* Context fields */}
          <div className="card" style={{ padding: 24 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
              <div>
                <Label>Target Market</Label>
                <Input value={form.target} onChange={set('target')} placeholder="e.g. United States, UK, Global" />
              </div>
              <div>
                <Label>Target Audience</Label>
                <Input value={form.audience} onChange={set('audience')} placeholder="e.g. B2B founders, startup CTOs" />
              </div>
            </div>
            <Label>Domain / Website</Label>
            <Input value={form.domain} onChange={set('domain')} placeholder="e.g. yoursite.com (for internal linking context)" />
          </div>

          {/* Notes */}
          <div className="card" style={{ padding: 24 }}>
            <Label>Additional Notes</Label>
            <textarea
              value={form.notes}
              onChange={set('notes')}
              placeholder="Any specific angle, competitors to beat, content format requirements…"
              rows={3}
              style={{
                width: '100%', padding: '11px 14px',
                background: 'white', border: '1px solid #E5E5E0',
                borderRadius: 8, fontSize: 14, color: '#0A0A0A',
                fontFamily: 'Plus Jakarta Sans, sans-serif',
                outline: 'none', resize: 'none',
                transition: 'border-color 0.15s, box-shadow 0.15s',
              }}
              onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
              onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }}
            />
          </div>

          {error && (
            <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, padding: '12px 16px', fontSize: 13, color: '#DC2626' }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !form.task.trim()}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '13px 24px',
              background: loading || !form.task.trim() ? '#C8C8C0' : '#0041FF',
              color: '#FFFFFF',
              border: 'none', borderRadius: 8, cursor: loading || !form.task.trim() ? 'not-allowed' : 'pointer',
              ...syne, fontSize: 13, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
              transition: 'opacity 0.15s',
            }}
          >
            {loading ? (
              <>
                <span style={{ width: 13, height: 13, border: '2px solid rgba(255,255,255,0.4)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                Starting Pipeline…
              </>
            ) : (
              <><Play size={13} /> Launch Agent Run</>
            )}
          </button>
        </form>

        {/* Pipeline preview */}
        <div>
          <div className="card overflow-hidden" style={{ marginBottom: 16 }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid #E5E5E0', ...syne, fontSize: 11, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Pipeline Stages
            </div>
            <div style={{ padding: '8px 0' }}>
              {STAGES.map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, padding: '10px 18px', position: 'relative' }}>
                  {i < STAGES.length - 1 && (
                    <div style={{ position: 'absolute', left: 26, top: 34, width: 1, height: 20, background: '#E5E5E0' }} />
                  )}
                  <div style={{
                    width: 24, height: 24, borderRadius: 6, border: '1px solid #E5E5E0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82',
                    flexShrink: 0, background: 'white',
                  }}>
                    {s.n}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#0A0A0A' }}>{s.label}</div>
                    <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 2 }}>{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 12, padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: '#059669', marginBottom: 6 }}>
              <Info size={11} /> Smart Caching
            </div>
            <div style={{ fontSize: 11, color: '#6B7280', lineHeight: 1.6 }}>
              Each stage output is saved as JSON. If a run fails, resume picks up from the last completed stage — no API tokens wasted.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
