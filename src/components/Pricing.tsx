import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'

export default function Pricing() {
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
    <section style={{
      padding: isDesktop ? '96px 0 32px' : '64px 0 16px',
      backgroundColor: '#EDEDED'
    }}>
      <h2 style={{
        fontSize: isDesktop ? '48px' : '32px',
        color: '#BFBFBF',
        textAlign: 'center',
        marginBottom: isDesktop ? '32px' : '16px'
      }}>
        {t('pricing.title')}
      </h2>
      <div style={{
        display: 'flex',
        gap: isDesktop ? '48px' : '32px',
        justifyContent: 'flex-start',
        margin: isDesktop ? '64px auto' : '48px 0',
        overflowX:  'scroll',
        width: '100%',
        maxWidth:isDesktop?'fit-content' :  '100%',
        paddingBottom: isDesktop ? '24px' : '8px',
        paddingLeft:  '16px',
        paddingRight: '16px',
        scrollbarWidth: 'none'
      }}>
        <div style={{
          background: '#fff',
          borderRadius: '18px',
          boxShadow: '0 4px 16px rgba(40, 60, 120, 0.10)',
          padding: isDesktop ? '48px 40px 48px 40px' : '32px 28px 32px 28px',
          minWidth: isDesktop ? '420px' : '80%',
          maxWidth: isDesktop ? '420px' : undefined,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          position: 'relative',
          textAlign: 'left',
          border: '2px solid #e3e8f0'
        }}>
          <div style={{
            marginBottom: '16px'
          }}>
            <h3 style={{
              fontSize: isDesktop ? '2rem' : '1.5rem',
              fontWeight: '700',
              margin: 0,
              color: '#222'
            }}>
              {t('pricing.freemium.title')}
            </h3>
            <p style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#888',
              marginTop: '4px'
            }}>
              {t('pricing.freemium.description')}
            </p>
          </div>
          <div style={{
            marginBottom: '12px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start'
          }}>
            <span style={{
              fontSize: isDesktop ? '2.6rem' : '2.2rem',
              fontWeight: '700',
              color: '#222'
            }}>
              {t('pricing.freemium.price')}
            </span>
            <span style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#888',
              marginTop: '2px'
            }}>
              {t('pricing.freemium.freeText')}
            </span>
          </div>
          <div style={{
            fontSize: isDesktop ? '1.1rem' : '0.95rem',
            color: '#2d4cff',
            marginBottom: '16px'
          }}>
            {t('pricing.freemium.note')}
          </div>
          <ul style={{
            listStyle: 'none',
            padding: 0,
            margin: '8px 0 0 0'
          }}>
            <li style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginBottom: '10px',
              paddingLeft: '24px',
              position: 'relative'
            }}>
              <span style={{
                content: '✓',
                position: 'absolute',
                left: 0,
                color: '#222',
                fontSize: isDesktop ? '1.3rem' : '1.1rem'
              }}>✓</span>
              {t('pricing.freemium.features.updates')}
            </li>
            <li style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginBottom: '10px',
              paddingLeft: '24px',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                left: 0,
                color: '#222',
                fontSize: isDesktop ? '1.3rem' : '1.1rem'
              }}>✓</span>
              {t('pricing.freemium.features.externalConnect')}
            </li>
            <li style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginBottom: '10px',
              paddingLeft: '24px',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                left: 0,
                color: '#222',
                fontSize: isDesktop ? '1.3rem' : '1.1rem'
              }}>✓</span>
              {t('pricing.freemium.features.connectableServices')}
            </li>
            <li style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginBottom: '10px',
              paddingLeft: '24px',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                left: 0,
                color: '#222',
                fontSize: isDesktop ? '1.3rem' : '1.1rem'
              }}>✓</span>
              {t('pricing.freemium.features.offload')}
            </li>
            <li style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginBottom: '10px',
              paddingLeft: '24px',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                left: 0,
                color: '#222',
                fontSize: isDesktop ? '1.3rem' : '1.1rem'
              }}>✓</span>
              {t('pricing.freemium.features.goalSetting')}
            </li>
          </ul>
        </div>
        <div style={{
          background: '#fff',
          borderRadius: '18px',
          boxShadow: '0 4px 16px rgba(40, 60, 120, 0.10)',
          padding: isDesktop ? '48px 40px 48px 40px' : '32px 28px 32px 28px',
          minWidth: isDesktop ? '420px' : '80%',
          maxWidth: isDesktop ? '420px' : undefined,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          position: 'relative',
          textAlign: 'left',
          border: '2px solid #2d4cff'
        }}>
          <div style={{
            marginBottom: '16px'
          }}>
            <h3 style={{
              fontSize: isDesktop ? '2rem' : '1.5rem',
              fontWeight: '700',
              margin: 0,
              color: '#2d4cff'
            }}>
              {t('pricing.plus.title')}
            </h3>
            <span style={{
              position: 'absolute',
              top: '24px',
              right: '24px',
              background: '#2d4cff',
              color: '#fff',
              fontSize: '0.8rem',
              fontWeight: '700',
              borderRadius: '12px',
              padding: '4px 12px',
              letterSpacing: '1px'
            }}>
              {t('pricing.plus.popular')}
            </span>
          </div>
          <div style={{
            marginBottom: '12px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start'
          }}>
            <span style={{
              fontSize: isDesktop ? '2.6rem' : '2.2rem',
              fontWeight: '700',
              color: '#2d4cff'
            }}>
              {t('pricing.plus.price')}
            </span>
            <span style={{
              fontSize: isDesktop ? '1.2rem' : '1rem',
              color: '#222',
              marginTop: '2px'
            }}>
              {t('pricing.plus.period')}
            </span>
            <span style={{
              fontSize: isDesktop ? '1.1rem' : '0.95rem',
              color: '#888',
              marginTop: '2px'
            }}>
              {t('pricing.plus.monthly')}
            </span>
          </div>
          <a 
            href="https://apps.apple.com/us/app/ai-mentor-app/id6745385262" 
            target="_blank" 
            rel="noopener"
            style={{
              width: '100%',
              display: 'inline-block',
              background: '#2d4cff',
              color: '#fff',
              fontWeight: '700',
              fontSize: isDesktop ? '1.3rem' : '1.1rem',
              borderRadius: '12px',
              padding: isDesktop ? '16px 40px' : '12px 32px',
              marginBottom: '18px',
              textAlign: 'center',
              textDecoration: 'none',
              boxShadow: '0 2px 8px rgba(40, 60, 120, 0.10)',
              transition: 'background 0.2s'
            }}
          >
            {t('pricing.plus.buttonText')}
          </a>
          <ul style={{
            listStyle: 'none',
            padding: 0,
            margin: '8px 0 0 0'
          }}>
            {[
              'updates',
              'unlimitedGeneration',
              'externalConnect',
              'connectableServices',
              'communicationSupport',
              'unlimitedOffload',
              'unlimitedFollowThrough',
              'goalSetting',
              'noAds'
            ].map((feature, index) => (
              <li key={index} style={{
                fontSize: isDesktop ? '1.2rem' : '1rem',
                color: '#222',
                marginBottom: '10px',
                paddingLeft: '24px',
                position: 'relative'
              }}>
                <span style={{
                  position: 'absolute',
                  left: 0,
                  color: '#2d4cff',
                  fontSize: isDesktop ? '1.3rem' : '1.1rem'
                }}>✓</span>
                {t(`pricing.plus.features.${feature}`)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}