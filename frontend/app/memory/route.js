import { NextResponse } from 'next/server'

const B = process.env.BACKEND_URL

export async function GET() {
  const res = await fetch(`${B}/memory`, { cache: 'no-store' })
  return NextResponse.json(await res.json())
}
