'use client'
import { useEffect, useState } from 'react'
import { Save, Eye, EyeOff, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

const FIELDS = [
  { key: 'OPENROUTER_API_KEY', label: 'OpenRouter API Key', secret: true, placeholder: 'sk-or-...', desc: 'Required for all agents.', link: 'https://openrouter.ai/keys' },
  { key: 'SERPER_API_KEY',     label: 'Serper.dev API Key', secret: true, placeholder: 'Your Serper key', desc: 'For SERP analysis.', link: 'https://serper.dev' },
  { key: 'DATAFORSEO_LOGIN',   label: 'DataForSEO Login',   secret: false, placeholder: 'your@email.com', desc: 'For keyword volume + difficulty data' },
  { key: 'DATAFORSEO_PASSWORD',label: 'DataForSEO Password',secret: true, placeholder: '••••••••', desc: 'DataForSEO account password' },
  { key: 'GSC_CREDENTIALS_PATH',label: 'GSC Credentials Path', secret: false, placeholder: '/data/gsc-credentials.json', desc: 'Absolute path to your GSC service account JSON file' },
  { key: 'GA4_CREDENTIALS_PATH',label: 'GA4 Credentials Path', secret: false, placeholder: '/data/ga4-credentials.json', desc: 'Absolute path to your GA4 service account JSON file' },
  { key: 'GA4_PROPERTY_ID',    label: 'GA4 Property ID', secret: false, placeholder: 'properties/123456789', desc: 'Your GA4 property ID (GA4 Admin → Property Settings)' },
]

const MODEL_GROUPS = [
  { label: 'Anthropic', models: [
    { value: 'anthropic/claude-sonnet-4-5', label: 'Claude Sonnet 4.5' },
    { value: 'anthropic/claude-haiku-4-5',  label: 'Claude Haiku 4.5 (fast + cheap)' },
    { value: 'anthropic/claude-opus-4-5',   label: 'Claude Opus 4.5 (most capable)' },
  ]},
  { label: 'OpenAI', models: [
    { value: 'openai/gpt-4o',      label: 'GPT-4o' },
    { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini (cheap)' },
  ]},
  { label: 'Google', models: [
    { value: 'google/gemini-flash-2.0', label: 'Gemini Flash 2.0 (fast)' },
    { value: 'google/gemini-pro-1.5',   label: 'Gemini Pro 1.5' },
  ]},
  { label: 'Meta / Open Source', models: [
    { value: 'meta-llama/llama-3.3-70b-instruct', label: 'Llama 3.3 70B' },
    { value: 'deepseek/deepseek-chat',             label: 'DeepSeek V3 (very cheap)' },
  ]},
]

const AGENT_MODELS = [
  { key: 'research_model', label: 'Research Agent',  desc: 'Keyword research + SERP analysis' },
  { key: 'content_model',  label: 'Content Agent',   desc: 'Outline + full article writing' },
  { key: 'onpage_model',   label: 'On-Page Agent',   desc: 'Scoring + optimization' },
  { key: 'links_model',    label: 'Links Agent',     desc: 'Cluster + internal linking' },
  { key: 'memory_model',   label: 'Memory Agent',    desc: 'Learning extraction' },
]

const inputStyle = { width: '100%', padding: '10px 14px', background: 'white', border: '1px solid #E5E5E0', borderRadius: 8, fontSize: 13, color: '#0A0A0A', fontFamily: 'Plus Jakarta Sans, sans-serif', outline: 'none', transition: 'border-color 0.15s, box-shadow 0.15s' }

function SectionCard({ title, subtitle, children }) {
  return (
    <div className="card overflow-hidden" style={{ marginBottom: 20 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8' }}>
        <div style={{ ...syne, fontSize: 12, fontWeight: 700, color: '#0A0A0A', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{title}</div>
        {subtitle && <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 2 }}>{subtitle}</div>}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </div>
  )
}

function ModelSelect({ value, onChange }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ ...inputStyle }}
      onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
      onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }}>
      {MODEL_GROUPS.map(g => (
        <optgroup key={g.label} label={g.label}>
          {g.models.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
        </optgroup>
      ))}
    </select>
  )
}

export default function SettingsPage() {
  const [config, setConfig]         = useState({})
  const [modelSettings, setModel]   = useState({ model: 'anthropic/claude-sonnet-4-5', research_model: 'openai/gpt-4o-mini', content_model: 'anthropic/claude-sonnet-4-5', onpage_model: 'openai/gpt-4o-mini', links_model: 'openai/gpt-4o-mini', memory_model: 'openai/gpt-4o-mini', max_tokens: 4096, temperature: 0.3 })
  const [pipeline, setPipeline]     = useState({ max_retries: 3, retry_delay: 5, timeout_per_stage: 120 })
  const [visible, setVisible]       = useState({})
  const [saving, setSaving]         = useState(false)
  const [saved, setSaved]           = useState(false)
  const [loading, setLoading]       = useState(true)

  useEffect(() => {
    fetch('/api/config').then(r => r.json()).then(d => {
      setConfig(d.env || {})
      if (d.model) setModel(p => ({ ...p, ...d.model }))
      if (d.pipeline) setPipeline(d.pipeline)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ env: config, model: modelSettings, pipeline }) })
    setSaving(false); setSaved(true); setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 720 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Configuration</div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', marginBottom: 4 }}>Settings</h1>
          <p style={{ fontSize: 13, color: '#8A8A82' }}>API keys · Model selection · Pipeline config</p>
        </div>
        <button onClick={handleSave} disabled={saving} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '11px 20px',
          background: saved ? '#059669' : '#0041FF', color: 'white',
          border: 'none', borderRadius: 8, cursor: saving ? 'not-allowed' : 'pointer',
          ...syne, fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
          opacity: saving ? 0.7 : 1, transition: 'background 0.3s',
        }}>
          {saving ? <span style={{ width: 13, height: 13, border: '2px solid rgba(255,255,255,0.4)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                  : saved ? <CheckCircle size={13} /> : <Save size={13} />}
          {saved ? 'Saved!' : 'Save Config'}
        </button>
      </div>

      {saved && (
        <div style={{ marginBottom: 20, background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 8, padding: '12px 16px', fontSize: 13, color: '#059669', display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle size={14} /> Configuration saved — restart dev server for API key changes to take effect
        </div>
      )}

      {/* API Keys */}
      <SectionCard title="API Keys" subtitle="Stored in .env.local — never sent to the browser">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {FIELDS.map(field => (
            <div key={field.key}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ fontSize: 13, fontWeight: 500, color: '#0A0A0A' }}>{field.label}</label>
                  {field.link && (
                    <a href={field.link} target="_blank" rel="noreferrer" style={{ color: '#C8C8C0', lineHeight: 0 }}
                      onMouseEnter={e => e.currentTarget.style.color = '#0041FF'}
                      onMouseLeave={e => e.currentTarget.style.color = '#C8C8C0'}>
                      <ExternalLink size={11} />
                    </a>
                  )}
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20, background: config[field.key] ? '#ECFDF5' : '#F3F3EF', color: config[field.key] ? '#059669' : '#8A8A82' }}>
                  {config[field.key] ? '● Connected' : '○ Not set'}
                </span>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type={field.secret && !visible[field.key] ? 'password' : 'text'}
                  value={config[field.key] || ''}
                  onChange={e => setConfig(c => ({ ...c, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                  style={{ ...inputStyle, paddingRight: field.secret ? 40 : 14 }}
                  onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
                  onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }}
                />
                {field.secret && (
                  <button onClick={() => setVisible(v => ({ ...v, [field.key]: !v[field.key] }))}
                    style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#C8C8C0', padding: 0 }}
                    onMouseEnter={e => e.currentTarget.style.color = '#8A8A82'}
                    onMouseLeave={e => e.currentTarget.style.color = '#C8C8C0'}>
                    {visible[field.key] ? <EyeOff size={13} /> : <Eye size={13} />}
                  </button>
                )}
              </div>
              <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 5 }}>{field.desc}</div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Default Model */}
      <SectionCard title="Default Model" subtitle="Used when no per-agent override is set">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#0A0A0A', marginBottom: 6 }}>Fallback Model</label>
            <ModelSelect value={modelSettings.model} onChange={v => setModel(m => ({ ...m, model: v }))} />
          </div>
          <div className="grid-2col">
            {[
              { key: 'max_tokens', label: 'Max Tokens', min: 1000, max: 8192, step: 256, format: v => v },
              { key: 'temperature', label: 'Temperature', min: 0, max: 1, step: 0.1, format: v => v },
            ].map(s => (
              <div key={s.key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <label style={{ fontSize: 12, fontWeight: 500, color: '#0A0A0A' }}>{s.label}</label>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#0041FF' }}>{s.format(modelSettings[s.key])}</span>
                </div>
                <input type="range" min={s.min} max={s.max} step={s.step} value={modelSettings[s.key]}
                  onChange={e => setModel(m => ({ ...m, [s.key]: s.key === 'temperature' ? parseFloat(e.target.value) : parseInt(e.target.value) }))}
                  style={{ width: '100%', accentColor: '#0041FF' }} />
              </div>
            ))}
          </div>
        </div>
      </SectionCard>

      {/* Per-Agent Models */}
      <SectionCard title="Per-Agent Model Overrides" subtitle="Use cheap models for analysis, best model for writing">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {AGENT_MODELS.map(agent => (
            <div key={agent.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: '#0A0A0A' }}>{agent.label}</label>
                <span style={{ fontSize: 11, color: '#8A8A82' }}>{agent.desc}</span>
              </div>
              <ModelSelect value={modelSettings[agent.key] || modelSettings.model} onChange={v => setModel(m => ({ ...m, [agent.key]: v }))} />
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Pipeline */}
      <SectionCard title="Pipeline Settings">
        <div className="grid-3col">
          {[
            { key: 'max_retries', label: 'Max Retries', min: 1, max: 10 },
            { key: 'retry_delay', label: 'Retry Delay (sec)', min: 1, max: 60 },
            { key: 'timeout_per_stage', label: 'Stage Timeout (sec)', min: 30, max: 600 },
          ].map(f => (
            <div key={f.key}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#0A0A0A', marginBottom: 6 }}>{f.label}</label>
              <input type="number" min={f.min} max={f.max} value={pipeline[f.key]}
                onChange={e => setPipeline(p => ({ ...p, [f.key]: parseInt(e.target.value) }))}
                style={inputStyle}
                onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
                onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }} />
            </div>
          ))}
        </div>
      </SectionCard>

      <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 10, padding: '14px 16px', display: 'flex', gap: 10 }}>
        <AlertCircle size={14} style={{ color: '#D97706', flexShrink: 0, marginTop: 1 }} />
        <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.6 }}>
          API keys are written to <strong style={{ color: '#0A0A0A' }}>.env.local</strong>. Model and pipeline settings go to <strong style={{ color: '#0A0A0A' }}>config.json</strong>. Restart the dev server after saving API key changes.
        </div>
      </div>
    </div>
  )
}
