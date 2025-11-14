'use client'

import i18n from '../../lib/i18n'
import Header from '@/components/Header'
import Hero from '@/components/Hero'
import Pricing from '@/components/Pricing'
import Footer from '@/components/Footer'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import Section2 from '@/components/Section2'
import Section3 from '@/components/Section3'

export default function LocalePage({ params: { locale } }: { params: { locale: string } }) {
  // Set language immediately when component initializes
  i18n.changeLanguage(locale)

  return (
      <main>
      <Header />
      <LanguageSwitcher currentLocale="ja" />
      <div className="content">
        <Hero />
        <Section2 />
        <Section3 />
        <Pricing />
        <Footer />
      </div>
    </main>
  )
}