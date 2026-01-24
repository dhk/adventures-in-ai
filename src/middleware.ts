import { auth } from '@/app/api/auth/[...nextauth]/route'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const session = await auth()
  const isAuthRoute = request.nextUrl.pathname.startsWith('/api/auth')
  const isPublicRoute = request.nextUrl.pathname === '/' || 
                       request.nextUrl.pathname.startsWith('/auth')

  // Allow public routes and auth routes
  if (isAuthRoute || isPublicRoute) {
    return NextResponse.next()
  }

  // Protect all other routes
  if (!session) {
    // For API routes, return 401
    if (request.nextUrl.pathname.startsWith('/api')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    // For other routes, redirect to home
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
} 