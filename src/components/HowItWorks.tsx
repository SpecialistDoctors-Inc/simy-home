'use client'

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Section6 from './Section6'

export default function HowItWorks() {
  const { t } = useTranslation()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isDesktop, setIsDesktop] = useState(false)

  const avatars = [
    '/img/avatar2.png',
    '/img/avatar3.png',
    '/img/avatar6.png'
  ]

  useEffect(() => {
    const checkScreen = () => {
      setIsDesktop(window.innerWidth >= 768)
    }
    checkScreen()
    window.addEventListener('resize', checkScreen)
    return () => window.removeEventListener('resize', checkScreen)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % avatars.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [avatars.length])

  return (
    <>
      <section style={isDesktop
        ? {
            backgroundColor: 'black',
            padding: '120px 40px 60px',
            borderBottom: '1px solid #eee',
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'nowrap',
          }
        : {
            backgroundColor: 'black',
            padding: '80px 16px 40px',
            borderBottom: '1px solid #eee',
            textAlign: 'left'
          }
      }>
        <div>
         <h3 style={isDesktop
          ? {
              color: 'white',
              fontSize: '3rem',
              fontWeight: 'bold',
              marginBottom: '24px',
              whiteSpace: 'pre-line'
            }
          : {
              color: 'white',
              fontSize: 'clamp(2.4rem, 6vw, 2rem)',
              fontWeight: 'bold',
              marginBottom: '12px',
              whiteSpace: 'pre-line'
            }
        }>
          {t('howItWorks.title')}
        </h3>
        <h4 style={isDesktop
          ? {
              fontSize: '1.6rem',
              color: 'white',
              padding: '24px 0 28px 0',
              lineHeight: '1.6',
              whiteSpace: 'pre-line',
            }
          : {
              fontSize: 'clamp(0.8rem, 3vw, 1.2rem)',
              color: 'white',
              padding: '17px 0 20px 0',
              lineHeight: '1.4',
              whiteSpace: 'pre-line',
            }
        }
        dangerouslySetInnerHTML={{ __html: t('howItWorks.subtitle') }} />
        <p style={isDesktop
          ? {
              color: 'white',
              fontSize: '1.2rem',
              whiteSpace: 'pre-line',
              lineHeight: '1.6',
            }
          : {
              color: 'white',
              fontSize: '0.8rem',
              whiteSpace: 'pre-line',
              lineHeight: '1.4',
            }
        }
        dangerouslySetInnerHTML={{ __html: t('howItWorks.description') }} />
       </div> <div style={isDesktop
          ? {
              position: 'relative',
              width: '100%',
              maxWidth: '480px',
              overflow: 'hidden',
              borderRadius: '24px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.10)',
              padding: '16px 0 48px 0'
            }
          : {
              position: 'relative',
              width: '100%',
              maxWidth: '340px',
              margin: '32px auto 0 auto',
              overflow: 'hidden',
              borderRadius: '16px',
              boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
              padding: '8px 0 32px 0'
            }
        }>
          <div style={{
            display: 'flex',
            flexDirection: 'row',
            justifyContent: 'center',
            alignItems: 'center'
          }}>
            {avatars.map((avatar, index) => (
              <img
                key={index}
                src={avatar}
                alt={`SIMY Avatar ${index + 1}`}
                style={isDesktop
                  ? {
                      width: '80%',
                      objectFit: 'contain',
                      borderRadius: '18px',
                      boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
                      display: index === currentIndex ? 'block' : 'none',
                      margin: '0 auto'
                    }
                  : {
                      width: '80%',
                      objectFit: 'contain',
                      borderRadius: '12px',
                      boxShadow: '0 1px 6px rgba(0,0,0,0.04)',
                      display: index === currentIndex ? 'block' : 'none',
                      margin: '0 auto'
                    }
                }
              />
            ))}
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '6px',
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: '12px',
            zIndex: 2
          }}>
            {avatars.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentIndex(index)}
                aria-label={`Show avatar ${index + 1}`}
                style={isDesktop
                  ? {
                      width: index === currentIndex ? '40px' : '14px',
                      height: '14px',
                      borderRadius: '18px',
                      background: index === currentIndex ? '#2a4d7c' : 'white',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }
                  : {
                      width: index === currentIndex ? '30px' : '10px',
                      height: '10px',
                      borderRadius: '14px',
                      background: index === currentIndex ? '#2a4d7c' : 'white',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }
                }
              />
            ))}
          </div>
        </div>
      </section>

      <Section6 />
    </>
  )
}