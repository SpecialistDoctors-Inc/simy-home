import { useTranslation } from 'react-i18next'
import Section2 from './Section2'
import Section3 from './Section3'
import Section4 from './Section4'
import Section5 from './Section5'

export default function Hero() {
  const { t } = useTranslation()

  return (
    <>
      <section className="hero">
        <img 
          src="/img/1.png" 
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