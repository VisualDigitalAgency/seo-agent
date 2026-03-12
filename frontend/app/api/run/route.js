// app/api/run/route.js
import { NextResponse } from 'next/server'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function POST(request) {
  const body = await request.json()
  const res  = await fetch(`${B}/run`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
