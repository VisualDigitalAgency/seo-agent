'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Play, List, Brain, Settings,
  CalendarClock, Wrench, Menu, X,
} from 'lucide-react'

const navItems = [
  { href: '/',          label: 'Dashboard',    icon: LayoutDashboard },
  { href: '/task',      label: 'New Task',     icon: Play },
  { href: '/runs',      label: 'Runs',         icon: List },
  { href: '/scheduler', label: 'Scheduler',    icon: CalendarClock },
  { href: '/tools',     label: 'Tool Monitor', icon: Wrench },
  { href: '/memory',    label: 'Memory',       icon: Brain },
  { href: '/settings',  label: 'Settings',     icon: Settings },
]

export default function Sidebar() {
  const pathname       = usePathname()
  const [expanded, setExpanded] = useState(false)
  const [isTablet, setIsTablet] = useState(false)

  useEffect(() => {
    const check = () => setIsTablet(window.innerWidth <= 1024)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Close overlay when navigating
  useEffect(() => { setExpanded(false) }, [pathname])

  const collapsed = isTablet && !expanded
  const showOverlay = isTablet && expanded

  const sidebarWidth = collapsed ? 64 : 240

  return (
    <>
      {/* Backdrop on tablet expand */}
      {showOverlay && (
        <div
          className="sidebar-backdrop visible"
          onClick={() => setExpanded(false)}
        />
      )}

      <aside
        style={{
          position: 'fixed',
          left: 0, top: 0,
          height: '100%',
          width: sidebarWidth,
          background: '#FFFFFF',
          borderRight: '1px solid #E5E5E0',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 50,
          transition: 'width 0.25s ease',
          overflow: 'hidden',
        }}
      >
        {/* Logo / Toggle */}
        <div style={{
          padding: collapsed ? '20px 0' : '24px 20px',
          borderBottom: '1px solid #E5E5E0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          minHeight: 72,
        }}>
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden' }}>
              <div style={{
                width: 32, height: 32, background: '#0041FF', borderRadius: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'white', fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 15,
                flexShrink: 0,
              }}>
                S
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 15, color: '#0A0A0A', letterSpacing: '-0.3px', whiteSpace: 'nowrap' }}>
                  SEO Agent
                </div>
                <div style={{ fontSize: 11, color: '#8A8A82', whiteSpace: 'nowrap' }}>Autonomous Pipeline</div>
              </div>
            </div>
          )}

          {/* On tablet: show logo mark when collapsed, X when expanded */}
          {isTablet && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{
                width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: expanded ? '#F3F3EF' : '#0041FF',
                border: 'none', borderRadius: 8, cursor: 'pointer',
                color: expanded ? '#3D3D38' : '#FFFFFF',
                flexShrink: 0,
              }}
            >
              {expanded ? <X size={15} /> : <Menu size={15} />}
            </button>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: collapsed ? '12px 0' : '16px 10px', display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? label : undefined}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: collapsed ? 0 : 10,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  padding: collapsed ? '10px 0' : '9px 12px',
                  borderRadius: collapsed ? 0 : 8,
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  color: active ? '#0041FF' : '#3D3D38',
                  background: active && !collapsed ? '#EEF1FF' : 'transparent',
                  textDecoration: 'none',
                  transition: 'all 0.15s',
                  borderLeft: !collapsed && active ? '3px solid #0041FF' : '3px solid transparent',
                  position: 'relative',
                }}
                onMouseEnter={e => {
                  if (!active) {
                    e.currentTarget.style.background = '#F3F3EF'
                    e.currentTarget.style.color = '#0A0A0A'
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    e.currentTarget.style.background = 'transparent'
                    e.currentTarget.style.color = '#3D3D38'
                  }
                }}
              >
                <Icon
                  size={16}
                  style={{
                    flexShrink: 0,
                    color: active ? '#0041FF' : 'inherit',
                  }}
                />
                {!collapsed && <span style={{ whiteSpace: 'nowrap' }}>{label}</span>}

                {/* Active dot on collapsed */}
                {collapsed && active && (
                  <span style={{
                    position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                    width: 5, height: 5, borderRadius: '50%', background: '#0041FF',
                  }} />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div style={{
          padding: collapsed ? '12px 0' : '12px 16px',
          borderTop: '1px solid #E5E5E0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: 8,
        }}>
          <span
            style={{ width: 7, height: 7, borderRadius: '50%', background: '#059669', flexShrink: 0 }}
            className="animate-pulse"
          />
          {!collapsed && (
            <>
              <span style={{ fontSize: 11, color: '#8A8A82' }}>System Ready</span>
              <span style={{ fontSize: 11, color: '#C8C8C0', marginLeft: 'auto' }}>v1.0.0</span>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
