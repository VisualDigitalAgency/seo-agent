'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Play, List, Brain, Settings, Activity, Zap, CalendarClock, Wrench } from 'lucide-react'

const navItems = [
  { href: '/',          label: 'Dashboard',  icon: LayoutDashboard },
  { href: '/task',      label: 'New Task',   icon: Play },
  { href: '/runs',      label: 'Runs',       icon: List },
  { href: '/scheduler', label: 'Scheduler',  icon: CalendarClock },
  { href: '/tools',     label: 'Tool Monitor', icon: Wrench },
  { href: '/memory',    label: 'Memory',     icon: Brain },
  { href: '/settings',  label: 'Settings',   icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface border-r border-border flex flex-col z-50">
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-accent/10 border border-accent/30 flex items-center justify-center">
            <Zap size={14} className="text-accent" />
          </div>
          <div>
            <div className="font-sans font-extrabold text-sm text-white tracking-tight">SEO Agent</div>
            <div className="text-xs text-muted">Autonomous Pipeline</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
          return (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded text-xs transition-all group
                ${active
                  ? 'bg-accent/10 border border-accent/20 text-accent'
                  : 'text-muted hover:text-white hover:bg-surface2 border border-transparent'}`}>
              <Icon size={14} className={active ? 'text-accent' : 'text-muted group-hover:text-white'} />
              <span className="tracking-wide">{label}</span>
              {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted">
          <Activity size={11} />
          <span>System Ready</span>
          <span className="ml-auto w-2 h-2 rounded-full bg-accent3 animate-pulse" />
        </div>
        <div className="mt-1 text-xs text-dim">v1.0.0 · Cloud</div>
      </div>
    </aside>
  )
}
