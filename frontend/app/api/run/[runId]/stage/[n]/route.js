import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request, { params }) {
  const { runId, n } = params
  const res  = await fetch(`${B}/api/run/${runId}/stage/${n}`, { cache: 'no-store' })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
