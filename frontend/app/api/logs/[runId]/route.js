import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request, { params }) {
  const { runId } = await params
  const url = new URL(request.url)
  const tail = url.searchParams.get('tail') || '200'
  const res  = await fetch(`${B}/logs/${runId}?tail=${tail}`, { cache: 'no-store' })
  return NextResponse.json(await res.json())
}
