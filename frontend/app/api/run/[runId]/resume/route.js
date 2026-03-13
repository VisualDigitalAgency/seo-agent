import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function POST(request, { params }) {
  const { runId } = await params
  const res  = await fetch(`${B}/api/run/${runId}/resume`, { method: 'POST' })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
