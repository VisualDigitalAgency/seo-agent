'use client'
import { useEffect, useState } from 'react'
import { Brain, Search, TrendingUp, Tag, Calendar } from 'lucide-react'

const syne = { fontFamily: 'Syne, sans-serif' }

export default function MemoryPage() {
  const [learnings, setLearnings] = useState([])
  const [history, setHistory]     = useState([])
  const [query, setQuery]         = useState('')
  const [loading, setLoading]     = useState(true)
  const [tab, setTab]             = useState('learnings')

  const fetchMemory = (q = '') => {
    setLoading(true)
    fetch(`/api/memory${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      .then(r => r.json())
      .then(d => { setLearnings(d.learnings || []); setHistory(d.history || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchMemory() }, [])

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Memory System</div>
          <h1 style={{ ...syne, fontSize: 36, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.5px', marginBottom: 4 }}>Memory</h1>
          <p style={{ fontSize: 13, color: '#8A8A82' }}>Accumulated learnings from all completed runs</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {[{ label: 'Learnings', value: learnings.length }, { label: 'Tasks', value: history.length }].map(s => (
            <div key={s.label} className="card" style={{ padding: '12px 18px', textAlign: 'center' }}>
              <div style={{ ...syne, fontSize: 24, fontWeight: 700, color: '#0A0A0A' }}>{s.value}</div>
              <div style={{ fontSize: 11, color: '#8A8A82', marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Search */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={13} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#C8C8C0' }} />
          <input
            type="text" value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchMemory(query)}
            placeholder="Search learnings by topic, keyword, insight…"
            style={{ width: '100%', padding: '11px 14px 11px 36px', background: 'white', border: '1px solid #E5E5E0', borderRadius: 8, fontSize: 13, color: '#0A0A0A', fontFamily: 'Plus Jakarta Sans, sans-serif', outline: 'none' }}
            onFocus={e => { e.target.style.borderColor = '#0041FF'; e.target.style.boxShadow = '0 0 0 3px rgba(0,65,255,0.10)' }}
            onBlur={e => { e.target.style.borderColor = '#E5E5E0'; e.target.style.boxShadow = 'none' }}
          />
        </div>
        <button onClick={() => fetchMemory(query)} style={{ padding: '11px 20px', background: '#0041FF', color: 'white', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
          Search
        </button>
        {query && (
          <button onClick={() => { setQuery(''); fetchMemory() }} style={{ padding: '11px 16px', background: 'white', border: '1px solid #E5E5E0', borderRadius: 8, fontSize: 13, color: '#8A8A82', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #E5E5E0', marginBottom: 24, display: 'flex', gap: 4 }}>
        {['learnings', 'history'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: '8px 16px', fontSize: 13, fontWeight: tab === t ? 600 : 400,
            color: tab === t ? '#0041FF' : '#8A8A82',
            borderBottom: tab === t ? '2px solid #0041FF' : '2px solid transparent',
            background: 'none', border: 'none', borderRadius: 0, cursor: 'pointer',
            textTransform: 'capitalize', marginBottom: -1, transition: 'color 0.15s',
          }}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#8A8A82', fontSize: 13 }}>Loading memory…</div>
      ) : tab === 'learnings' ? (
        learnings.length === 0 ? (
          <div className="card" style={{ padding: 60, textAlign: 'center', fontSize: 13, color: '#8A8A82' }}>
            {query ? `No learnings matching "${query}"` : 'No learnings yet. Complete runs to build memory.'}
          </div>
        ) : (
          <div className="grid-2col">
            {learnings.map((item, i) => (
              <div key={i} className="card" style={{ padding: 20, transition: 'box-shadow 0.15s' }}
                onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', lineHeight: 1.4, paddingRight: 12 }}>{item.task}</div>
                  {item.ranking && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, background: '#FFFBEB', border: '1px solid #FDE68A', color: '#D97706', padding: '3px 8px', borderRadius: 20, flexShrink: 0 }}>
                      <TrendingUp size={9} /> #{item.ranking}
                    </span>
                  )}
                </div>
                {item.insights?.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    {item.insights.map((ins, j) => (
                      <div key={j} style={{ display: 'flex', gap: 8, fontSize: 12, color: '#3D3D38', marginBottom: 4 }}>
                        <span style={{ color: '#059669', flexShrink: 0, fontWeight: 700 }}>›</span>
                        {ins}
                      </div>
                    ))}
                  </div>
                )}
                {item.skills_used?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                    {item.skills_used.map((s, j) => (
                      <span key={j} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, background: '#EEF1FF', border: '1px solid #C7D2FE', color: '#0041FF', padding: '2px 7px', borderRadius: 12 }}>
                        <Tag size={8} /> {s}
                      </span>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, color: '#8A8A82', paddingTop: 10, borderTop: '1px solid #F3F3EF' }}>
                  {item.traffic && <span>Traffic: <strong style={{ color: '#0A0A0A' }}>{item.traffic}</strong></span>}
                  {item.weeks_to_rank && <span>Ranked in: <strong style={{ color: '#0A0A0A' }}>{item.weeks_to_rank}w</strong></span>}
                  {item.date && (
                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Calendar size={9} /> {item.date}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="table-scroll"><div className="card overflow-hidden" style={{ minWidth: 560 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', padding: '10px 20px', borderBottom: '1px solid #E5E5E0', background: '#FAFAF8' }}>
            {['Task', 'Run ID', 'Status', 'Date'].map(h => (
              <div key={h} style={{ fontSize: 11, fontWeight: 600, color: '#8A8A82', letterSpacing: '0.07em', textTransform: 'uppercase' }}>{h}</div>
            ))}
          </div>
          {history.length === 0 ? (
            <div style={{ padding: 48, textAlign: 'center', fontSize: 13, color: '#8A8A82' }}>No task history yet</div>
          ) : history.map((row, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', padding: '12px 20px', borderBottom: '1px solid #E5E5E0', transition: 'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#FAFAF8'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ fontSize: 13, color: '#0A0A0A', fontWeight: 500 }}>{row.task}</div>
              <div style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#8A8A82' }}>{row.run_id}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: row.status === 'done' ? '#059669' : row.status === 'failed' ? '#DC2626' : '#8A8A82' }}>{row.status}</div>
              <div style={{ fontSize: 12, color: '#8A8A82' }}>{row.date}</div>
            </div>
          ))}
        </div></div>
      )}
    </div>
  )
}
