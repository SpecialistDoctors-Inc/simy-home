'use client'

import { useEffect } from 'react'
import '../lib/i18n'
import Header from '@/components/Header'
import Hero from '@/components/Hero'
import HowItWorks from '@/components/HowItWorks'
import WhoItsFor from '@/components/WhoItsFor'
import Pricing from '@/components/Pricing'
import CallToAction from '@/components/CallToAction'
import Integrations from '@/components/Integrations'
import Footer from '@/components/Footer'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { useTranslation } from 'react-i18next'

export default function Home() {
  const { i18n } = useTranslation()
  
  useEffect(() => {
    // Set default language to English for root path
    i18n.changeLanguage('en')
  }, [i18n])

  return (
    <main>
      <Header />
      <LanguageSwitcher currentLocale="en" />
      <div className="content">
        <Hero />
        <HowItWorks />
        <WhoItsFor />
        <Pricing />
        <CallToAction />
        <Integrations />
      </div>
      <Footer />
    </main>
  )
}