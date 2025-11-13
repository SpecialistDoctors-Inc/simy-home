'use client'

import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import '../lib/i18n'

type HeaderProps = {
  showInstallButton?: boolean;
};

export default function Header({ showInstallButton = false }: HeaderProps) {
  const { t } = useTranslation()
  const [isVisible, setIsVisible] = useState(true)
  const lastScrollY = useRef(0)

  useEffect(() => {
    const handleScroll = () => {
      // .content要素のスクロール位置を取得
      const contentElement = document.querySelector('.content')
      if (!contentElement) return
      
      const currentScrollY = contentElement.scrollTop

      // スクロール位置が50px以上の場合のみヘッダーの表示/非表示を制御
      if (currentScrollY > 50) {
        
        // 下にスクロールしている場合はヘッダーを隠す
        if (currentScrollY > lastScrollY.current && currentScrollY > 100) {
          setIsVisible(false)
        } 
        // 上にスクロールしている場合はヘッダーを表示
        else if (currentScrollY < lastScrollY.current) {
          setIsVisible(true)
        }
      } else {
        // ページトップ付近では常にヘッダーを表示
        setIsVisible(true)
      }

      lastScrollY.current = currentScrollY
    }

    // スクロールイベントにスロットリングを追加
    let ticking = false
    const throttledHandleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          handleScroll()
          ticking = false
        })
        ticking = true
      }
    }

    // .content要素にスクロールイベントリスナーを追加
    const contentElement = document.querySelector('.content')
    if (contentElement) {
      contentElement.addEventListener('scroll', throttledHandleScroll, { passive: true })
      return () => contentElement.removeEventListener('scroll', throttledHandleScroll)
    }
  }, [])

  return (
    <header className={`header fixed-header ${isVisible ? 'show' : 'hide'}`}>
      <div className="header-inner">
        <a href="/" className="logo-link-pc">
          <img
            src="/img/icon_large.png"
            alt="SIMY"
            className="logo"
          />
        </a>
        <a href="/" className="logo-link-mobile">
          <img
            src="/img/icon.png"
            alt="SIMY"
            className="logo"
          />
        </a>
        {showInstallButton ? (
          <a
            href="https://apps.apple.com/us/app/ai-mentor-app/id6745385262"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
          >
            {t('header.installApp')}
          </a>
        ) : (
          <a
            href="/login"
            className="header-btn"
          >
            {t('header.getStarted')}
          </a>
        )}
      </div>
    </header>
  )
}
