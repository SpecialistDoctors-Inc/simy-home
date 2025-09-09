import { useTranslation } from 'react-i18next'

export default function Integrations() {
  const { t } = useTranslation()

  return (
    <>
      <section>
        <img 
          src="/img/12.png" 
          alt={t('integrations.altText')}
        />
      </section>
      <section className="intergrates">
        <h2>{t('integrations.title')}</h2>
      </section>
    </>
  )
}