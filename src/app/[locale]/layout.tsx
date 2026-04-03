import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '../globals.css'
import { notFound } from 'next/navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SIMY',
  description: 'When you\'re stuck, ask an expert instantly. Real expert knowledge via AI avatars.',
}

const locales = [
  'en', 'ja', 'zh', 'ko', 'es', 'fr', 'de', 'it', 'pt', 'ru', 
  'ar', 'hi', 'tr', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'cs',
  'hu', 'th'
]

export default function LocaleLayout({
  children,
  params: { locale }
}: {
  children: React.ReactNode
  params: { locale: string }
}) {
  // Validate that the incoming `locale` parameter is valid
  if (!locales.includes(locale)) notFound()

  return children
}

export async function generateStaticParams() {
  return locales.map((locale) => ({ locale }))
}