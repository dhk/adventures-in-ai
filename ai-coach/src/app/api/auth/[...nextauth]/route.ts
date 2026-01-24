import NextAuth from 'next-auth'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { prisma } from '@/lib/db'
import GoogleProvider from 'next-auth/providers/google'
import GitHubProvider from 'next-auth/providers/github'

const handler = NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
  ],
  callbacks: {
    authorized({ auth, request }) {
      const isLoggedIn = !!auth?.user
      const isApiRoute = request.nextUrl.pathname.startsWith('/api')
      const isAuthRoute = request.nextUrl.pathname.startsWith('/auth')
      
      if (isApiRoute && !isAuthRoute) {
        return isLoggedIn
      }

      return true
    }
  },
  pages: {
    signIn: '/',
  },
})

export { handler as GET, handler as POST } 