import { useTranslation } from 'react-i18next'
import { useState, useEffect } from 'react'
import Section2 from './Section2'
import Section3 from './Section3'
import Section4 from './Section4'
import Section5 from './Section5'

export default function Hero() {
  const { t } = useTranslation()
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const checkScreen = () => {
      setIsDesktop(window.innerWidth >= 768)
    }
    checkScreen()
    window.addEventListener('resize', checkScreen)
    return () => window.removeEventListener('resize', checkScreen)
  }, [])

  return (
    <>
      <section className="hero">
        <img 
          src={isDesktop ? '/img/1_pc.jpg' : '/img/1.png'} 
          alt={t('hero.altText')}
        />
      </section>
      <Section2 />
      <Section3 />
      <Section4 />
      <Section5 />
    </>
  )
}