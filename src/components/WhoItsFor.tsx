'use client'

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function WhoItsFor() {
  const { t } = useTranslation()
  const [isDesktop, setIsDesktop] = useState(false)

  const targetUsers = [
    { key: 'founders', image: '/img/for1.png' },
    { key: 'projectManagers', image: '/img/for2.png' },
    { key: 'soloWorkers', image: '/img/for3.png' },
    { key: 'remoteTeams', image: '/img/for4.png' }
  ]

  useEffect(() => {
    const checkScreen = () => {
      setIsDesktop(window.innerWidth >= 768)
    }
    checkScreen()
    window.addEventListener('resize', checkScreen)
    return () => window.removeEventListener('resize', checkScreen)
  }, [])

  return (
    <section style={{
      padding: isDesktop ? '70px 12px' : '64px 0 0'
    }}>
      <h2 style={{
        fontSize: isDesktop ? '48px' : '32px',
        color: '#BFBFBF',
        textAlign: 'center',
        marginBottom: isDesktop ? '32px' : '16px'
      }}>
        {t('whoItsFor.title')}
      </h2>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        flexDirection: isDesktop ? 'row' : 'column',
        gap: isDesktop ? '8px' : '12px',
        width: '100%',
        justifyContent: isDesktop ? 'center' : undefined,
        alignItems: isDesktop ? 'stretch' : undefined
      }}>
        {targetUsers.map((user) => (
          <div key={user.key} style={{
            textAlign: 'left',
            flex: isDesktop ? '1' : undefined,
            maxWidth: isDesktop ? '320px' : undefined,
          }}>
            <p style={{
              display: 'flex',
              alignItems: isDesktop ? 'center' : 'flex-start',
              justifyContent: isDesktop ? 'center' : 'flex-start',
              height: isDesktop ? '10rem' : 'auto',
              margin:'auto',
              fontSize: isDesktop ? 'clamp(1rem, 2vw, 1.4rem)' : 'clamp(1.4rem, 3vw, 1.8rem)',
              padding: isDesktop ? '16px 8px' : '8px',
              fontWeight: '800',
              whiteSpace: 'pre-line',
              lineHeight: '1.4',
              textAlign: isDesktop ? 'center' : 'left',
            }}>
              {t(`whoItsFor.${user.key}.title`)}
            </p>
            <img 
              src={user.image} 
              alt={t(`whoItsFor.${user.key}.alt`)} 
              style={{
                width: '100%',
                height: 'auto',
                display: 'block',
                margin: isDesktop ? '0 auto' : '0 auto'
              }}
            />
          </div>
        ))}
      </div>
    </section>
  )
}