import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request, { params }) {
  const { runId } = await params
  const res  = await fetch(`${B}/api/run/${runId}`, { cache: 'no-store' })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function DELETE(request, { params }) {
  const { runId } = await params
  const res  = await fetch(`${B}/api/run/${runId}`, { method: 'DELETE' })
  const data = await res.json()
  return NextResponse.json(data)
}
