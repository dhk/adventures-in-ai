import React from 'react'
import { Inter } from 'next/font/google'
import { Toaster } from 'react-hot-toast'
import { SessionProvider } from '@auth/nextjs/react'
import { Auth } from '@/components/Auth'
import './globals.css'

const inter = Inter({ 
  subsets: ['latin'],
  display: 'swap',
})

export const metadata = {
  title: 'AI Coach - Your Personal Development Partner',
  description: 'Get personalized coaching and guidance powered by AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <SessionProvider>
          <header className="p-4 border-b">
            <Auth />
          </header>
          <main>
            {children}
          </main>
          <Toaster position="top-right" />
        </SessionProvider>
      </body>
    </html>
  )
} 