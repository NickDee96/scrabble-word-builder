import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Scrabble Word Builder',
  description:
    'Find every valid word you can play from your letters — ranked by score, with an interactive Scrabble board.',
  keywords: ['Scrabble', 'word finder', 'anagram solver', 'word game', 'Collins Scrabble Words'],
  authors: [{ name: 'Nick Mumero' }],
  openGraph: {
    title: 'Scrabble Word Builder',
    description: 'Find every valid word you can play from your letters — ranked by score.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  )
}
