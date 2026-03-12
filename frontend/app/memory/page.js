'use client'
import { useEffect, useState } from 'react'
import { Brain, Search, TrendingUp, Tag, Calendar } from 'lucide-react'

export default function MemoryPage() {
  const [learnings, setLearnings] = useState([])
  const [history, setHistory] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('learnings')

  const fetchMemory = (q = '') => {
    setLoading(true)
    fetch(`/api/memory${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      .then(r => r.json())
      .then(d => {
        setLearnings(d.learnings || [])
        setHistory(d.history || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchMemory() }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchMemory(query)
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
            <Brain size={10} className="text-accent3" /> Memory System
          </div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Memory</h1>
          <p className="text-muted text-xs mt-1">Accumulated learnings from all completed runs</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <div className="bg-surface border border-border rounded px-3 py-2">
            <span className="text-white font-bold">{learnings.length}</span> learnings
          </div>
          <div className="bg-surface border border-border rounded px-3 py-2">
            <span className="text-white font-bold">{history.length}</span> tasks
          </div>
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search learnings by topic, keyword, insight..."
              className="w-full bg-surface border border-border rounded pl-9 pr-4 py-2.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-accent/10 text-accent border border-accent/20 text-xs rounded hover:bg-accent/20 transition-colors">
            Search
          </button>
          {query && (
            <button type="button" onClick={() => { setQuery(''); fetchMemory() }}
              className="px-3 py-2 text-xs text-muted border border-border rounded hover:text-white transition-colors">
              Clear
            </button>
          )}
        </div>
      </form>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border pb-1">
        {['learnings', 'history'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs rounded-t transition-colors capitalize
              ${tab === t ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'}`}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-xs text-muted p-8 text-center">Loading memory...</div>
      ) : tab === 'learnings' ? (
        learnings.length === 0 ? (
          <div className="text-xs text-muted p-8 text-center bg-surface border border-border rounded">
            {query ? `No learnings matching "${query}"` : 'No learnings yet. Complete runs to build memory.'}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {learnings.map((item, i) => (
              <div key={i} className="bg-surface border border-border rounded p-5 hover:border-accent3/30 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="text-sm text-white font-bold leading-tight pr-4">{item.task}</div>
                  {item.ranking && (
                    <div className="flex items-center gap-1 text-xs bg-accent4/10 border border-accent4/20 text-accent4 px-2 py-1 rounded flex-shrink-0">
                      <TrendingUp size={9} />
                      #{item.ranking}
                    </div>
                  )}
                </div>

                {item.insights?.length > 0 && (
                  <div className="mb-3 space-y-1">
                    {item.insights.map((ins, j) => (
                      <div key={j} className="flex items-start gap-2 text-xs text-muted">
                        <span className="text-accent3 mt-0.5 flex-shrink-0">›</span>
                        {ins}
                      </div>
                    ))}
                  </div>
                )}

                {item.skills_used?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {item.skills_used.map((s, j) => (
                      <span key={j} className="text-xs bg-accent2/10 border border-accent2/20 text-purple-400 px-2 py-0.5 rounded flex items-center gap-1">
                        <Tag size={8} /> {s}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-4 text-xs text-muted pt-3 border-t border-border/50">
                  {item.traffic && <span>Traffic: <span className="text-white">{item.traffic}</span></span>}
                  {item.weeks_to_rank && <span>Ranked in: <span className="text-white">{item.weeks_to_rank}w</span></span>}
                  {item.date && (
                    <span className="flex items-center gap-1 ml-auto">
                      <Calendar size={9} />{item.date}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* History tab — CSV data */
        <div className="bg-surface border border-border rounded overflow-hidden">
          <div className="grid grid-cols-5 gap-4 px-4 py-2.5 border-b border-border bg-surface2 text-xs text-muted uppercase tracking-widest">
            <div className="col-span-2">Task</div>
            <div>Run ID</div>
            <div>Status</div>
            <div>Date</div>
          </div>
          {history.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted">No task history yet</div>
          ) : (
            history.map((row, i) => (
              <div key={i} className="grid grid-cols-5 gap-4 px-4 py-3 border-b border-border/50 hover:bg-surface2/50 transition-colors text-xs">
                <div className="col-span-2 text-white">{row.task}</div>
                <div className="text-muted font-mono">{row.run_id}</div>
                <div className={row.status === 'done' ? 'text-accent3' : row.status === 'failed' ? 'text-accent5' : 'text-muted'}>
                  {row.status}
                </div>
                <div className="text-muted">{row.date}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
