import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  const res  = await fetch(`${B}/runs`, { cache: 'no-store' })
  const data = await res.json()
  return NextResponse.json(data)
}
