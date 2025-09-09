'use client'

import { useTranslation } from 'react-i18next'

import { useRouter } from 'next/navigation'

export default function LanguageSwitcher({ currentLocale = 'en' }: { currentLocale?: string }) {
  const router = useRouter()

  const languages = [
    { code: 'en', name: 'English', path: '/' },
    { code: 'ja', name: '日本語', path: '/ja' },
    { code: 'zh', name: '中文', path: '/zh' },
    { code: 'ko', name: '한국어', path: '/ko' },
    { code: 'es', name: 'Español', path: '/es' },
    { code: 'fr', name: 'Français', path: '/fr' },
    { code: 'de', name: 'Deutsch', path: '/de' },
    { code: 'it', name: 'Italiano', path: '/it' },
    { code: 'pt', name: 'Português', path: '/pt' },
    { code: 'ru', name: 'Русский', path: '/ru' },
    { code: 'ar', name: 'العربية', path: '/ar' },
    { code: 'hi', name: 'हिन्दी', path: '/hi' },
    { code: 'tr', name: 'Türkçe', path: '/tr' },
    { code: 'pl', name: 'Polski', path: '/pl' },
    { code: 'nl', name: 'Nederlands', path: '/nl' },
    { code: 'sv', name: 'Svenska', path: '/sv' },
    { code: 'da', name: 'Dansk', path: '/da' },
    { code: 'no', name: 'Norsk', path: '/no' },
    { code: 'fi', name: 'Suomi', path: '/fi' },
    { code: 'cs', name: 'Čeština', path: '/cs' },
    { code: 'hu', name: 'Magyar', path: '/hu' },
    { code: 'th', name: 'ไทย', path: '/th' },
  ]

  const changeLanguage = (path: string) => {
    router.push(path)
  }

  return (
    <div style={{ position: 'fixed', top: '80px', right: '20px', zIndex: 1000 }}>
      <select 
        value={currentLocale} 
        onChange={(e) => {
          const selectedLang = languages.find(lang => lang.code === e.target.value)
          if (selectedLang) {
            changeLanguage(selectedLang.path)
          }
        }}
        style={{
          padding: '8px 12px',
          borderRadius: '6px',
          border: '1px solid #ddd',
          backgroundColor: 'white',
          fontSize: '14px'
        }}
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </div>
  )
}