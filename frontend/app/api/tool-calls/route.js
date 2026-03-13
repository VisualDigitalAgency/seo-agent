import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request) {
  const url   = new URL(request.url)
  const limit = url.searchParams.get('limit') || '100'
  const res   = await fetch(`${B}/tool-calls?limit=${limit}`, { cache: 'no-store' })
  const data  = await res.json()
  return NextResponse.json(data)
}
