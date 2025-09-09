import { useTranslation } from 'react-i18next'

export default function WhoItsFor() {
  const { t } = useTranslation()

  const targetUsers = [
    { key: 'founders', image: '/img/for1.png' },
    { key: 'projectManagers', image: '/img/for2.png' },
    { key: 'soloWorkers', image: '/img/for3.png' },
    { key: 'remoteTeams', image: '/img/for4.png' }
  ]

  return (
    <section style={{
      padding: '64px 0 0'
    }}>
      <h2 style={{
        fontSize: '32px',
        color: '#BFBFBF',
        textAlign: 'center',
        marginBottom: '16px'
      }}>
        {t('whoItsFor.title')}
      </h2>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        width: '100%'
      }}>
        {targetUsers.map((user) => (
          <div key={user.key} style={{
            textAlign: 'left'
          }}>
            <p style={{
              fontSize: 'clamp(1.4rem, 3vw, 1.8rem)',
              padding: '8px 8px 0',
              fontWeight: '800',
              whiteSpace: 'pre-line',
              margin: 0,
              lineHeight: '1.4',
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
                margin: '0 auto'
              }}
            />
          </div>
        ))}
      </div>
    </section>
  )
}