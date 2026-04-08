import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Integrations() {
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
      <section style={{backgroundColor:'#EDF5FF'}}>
        <img 
          src="/img/12.png" 
          alt={t('integrations.altText')}
          style={{
            width: isDesktop ? '60%' : '100%',
            height: 'auto',
            display: 'block',
            margin: isDesktop ? '0 auto' : '0 auto'
          }}
        />
      </section>
      <section className="intergrates">
        <h2 style={{
          fontSize: isDesktop ? '2.4rem' : '1.6rem',
          textAlign: isDesktop ? 'center' : 'left',
          margin: isDesktop ? '16px 0' : '16px 0',
        }}>{t('integrations.title')}</h2>
      </section>
    </>
  )
}