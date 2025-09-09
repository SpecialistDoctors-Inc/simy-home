'use client'

import { useTranslation } from 'react-i18next'

export default function Section5() {
  const { t } = useTranslation()

  return (
    <section style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
      <div style={{
        textAlign: 'left',
        color: '#000000',
        textShadow: 'none',
        padding: 'clamp(10px, 4vw, 20px)',
      }}>
        <h2 style={{
          fontSize: 'clamp(2.6rem, 6vw, 4rem)',
          fontWeight: 'bold',
          lineHeight: '1.1',
          whiteSpace: 'pre-line'
        }}>
          {t('sections.section5.title')}
        </h2>
      </div>
      <img 
        src="/img/5.png" 
        alt={t('hero.altText')}
        style={{ width: '100%', height: 'auto',
         }}
      />
        <div style={{
        bottom: '0',
        textAlign: 'left',
        color: 'black',
        textShadow: 'none',
        padding: 'clamp(20px, 4vw, 40px)',
      }}>
        <h3 style={{
          fontSize: 'clamp(1.6rem, 4vw, 2.4rem)',
          fontWeight: 'bold',
          wordSpacing: '0.1em',
          lineHeight: '1.2',
          margin: '4px 0 10px 0',
          whiteSpace: 'pre-line',
          textAlign: 'center'
        }}>
          {t('sections.section5.subtitle')}
        </h3>
        <p style={{
          fontSize: 'clamp(0.8rem, 3vw, 1.2rem)',
          whiteSpace: 'pre-line',
          lineHeight: '1.4',
          margin: '10px 0 0 0'
        }}>
          {t('sections.section5.description')}
        </p>
      </div>
    </section>
  )
}