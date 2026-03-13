export const dynamic = 'force-dynamic'
const B = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request, { params }) {
  const { runId } = params
  const backendRes = await fetch(`${B}/api/stream/${runId}`, {
    headers: { 'Accept': 'text/event-stream' },
    cache: 'no-store',
  })

  return new Response(backendRes.body, {
    headers: {
      'Content-Type':  'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection':    'keep-alive',
      'X-Accel-Buffering': 'no',
    }
  })
}
