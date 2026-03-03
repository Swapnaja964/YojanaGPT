import React from 'react'

type Props = {
  title?: string
  children: React.ReactNode
}

export default function Layout({ title = 'Government Scheme Recommendation Engine', children }: Props) {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {children}
      </main>
    </div>
  )
}
