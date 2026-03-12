import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata = {
  title: 'SEO Agent',
  description: 'Autonomous SEO Agent System',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen relative z-10">
          <Sidebar />
          <main className="flex-1 ml-64 p-8 min-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
