'use client'

import { useEffect } from 'react'
import i18n from '../../lib/i18n'
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

export default function LocalePage({ params: { locale } }: { params: { locale: string } }) {
  // Set language immediately when component initializes
  i18n.changeLanguage(locale)
  
  const { t } = useTranslation()

  return (
    <main>
      <Header />
      <LanguageSwitcher currentLocale={locale} />
      <div className="content">
        <Hero />
        <HowItWorks />
        <WhoItsFor />
        <Pricing />
        <CallToAction />
        <Integrations />
        <Footer />
      </div>
    </main>
  )
}