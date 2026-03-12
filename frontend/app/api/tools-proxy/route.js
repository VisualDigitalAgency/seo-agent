import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

// Proxy any POST to /tools/* through to backend
// Used by Tool Monitor tester when CORS prevents direct browser→backend calls
export async function POST(request) {
  const url      = new URL(request.url)
  const toolPath = url.searchParams.get('tool') || ''
  const body     = await request.json()

  if (!toolPath) return NextResponse.json({ error: 'tool param required' }, { status: 400 })

  const res  = await fetch(`${B}/tools/${toolPath}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function GET() {
  const res  = await fetch(`${B}/tools`, { cache: 'no-store' })
  const data = await res.json()
  return NextResponse.json(data)
}
