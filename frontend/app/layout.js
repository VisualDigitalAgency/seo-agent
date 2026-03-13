import './globals.css'
import Sidebar from '../components/Sidebar'

export const metadata = {
  title: 'SEO Agent',
  description: 'Autonomous SEO Agent System',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ background: '#FFFFFF' }}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="main-content min-h-screen bg-[#FAFAF8] flex-1">
            <div style={{ maxWidth: 1200, margin: '0 auto', padding: 'clamp(20px, 4vw, 40px) clamp(16px, 3vw, 32px)' }}>
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}
