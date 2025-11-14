'use client'

import { useEffect } from 'react'
import '../lib/i18n'
import Header from '@/components/Header'
import Hero from '@/components/Hero'
import Footer from '@/components/Footer'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { useTranslation } from 'react-i18next'
import Section2 from '@/components/Section2'
import Section3 from '@/components/Section3'
import Pricing from '@/components/Pricing'

export default function Home() {
  const { i18n } = useTranslation()
  
  useEffect(() => {
    i18n.changeLanguage('ja')
  }, [i18n])

  return (
    <main>
      <Header />
      {/* <LanguageSwitcher currentLocale="ja" /> */}
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