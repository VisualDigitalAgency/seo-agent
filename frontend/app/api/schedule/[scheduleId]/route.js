import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function DELETE(request, { params }) {
  const { scheduleId } = params
  const res  = await fetch(`${B}/api/schedules/${scheduleId}`, { method: 'DELETE' })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function POST(request, { params }) {
  // run-now — path: /api/schedule/[scheduleId]  with ?action=run-now
  const { scheduleId } = params
  const url   = new URL(request.url)
  const action = url.searchParams.get('action')

  if (action === 'run-now') {
    const res  = await fetch(`${B}/api/schedules/${scheduleId}/run-now`, { method: 'POST' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }

  return NextResponse.json({ error: 'unknown action' }, { status: 400 })
}
