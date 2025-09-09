'use client'

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function Header() {
  const { t } = useTranslation()
  const [isScrolled, setIsScrolled] = useState(false)
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY
      
      if (currentScrollY > 100) {
        setIsScrolled(true)
        if (currentScrollY > lastScrollY) {
          setIsVisible(false)
        } else {
          setIsVisible(true)
        }
      } else {
        setIsScrolled(false)
        setIsVisible(true)
      }
      
      setLastScrollY(currentScrollY)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lastScrollY])

  return (
    <header className={`header fixed-header ${isVisible ? 'show' : 'hide'}`}>
      <div className="header-inner">
        <img 
          src="/img/aim_logo_Horizontal_white.png" 
          alt="AI Mentor" 
          className="logo"
        />
        <a 
          href="https://apps.apple.com/us/app/ai-mentor-app/id6745385262" 
          target="_blank" 
          rel="noopener" 
          className="header-btn"
        >
          {t('header.getStarted')}
        </a>
      </div>
    </header>
  )
}