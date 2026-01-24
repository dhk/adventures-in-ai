'use client';

import React from 'react'
import { signIn, signOut, useSession } from 'next-auth/react'

export function Auth() {
  const { data: session } = useSession()

  return (
    <div className="flex justify-end items-center gap-4">
      {session ? (
        <>
          <span className="text-sm text-gray-600">
            Signed in as {session.user?.email}
          </span>
          <button
            onClick={() => signOut()}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Sign Out
          </button>
        </>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={() => signIn('google')}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Sign in with Google
          </button>
          <button
            onClick={() => signIn('github')}
            className="px-4 py-2 text-sm font-medium text-white bg-gray-800 rounded-md hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            Sign in with GitHub
          </button>
        </div>
      )}
    </div>
  )
} 