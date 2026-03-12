import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request) {
  const url = new URL(request.url)
  const q   = url.searchParams.get('q') || ''
  const res = await fetch(`${B}/memory${q ? `?q=${encodeURIComponent(q)}` : ''}`, { cache: 'no-store' })
  return NextResponse.json(await res.json())
}

export async function POST(request) {
  const body = await request.json()
  const res  = await fetch(`${B}/memory`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) })
  return NextResponse.json(await res.json())
}
