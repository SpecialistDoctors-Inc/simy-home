'use client'

import { useTranslation } from 'react-i18next'

interface ImageWithOverlayProps {
  imageSrc: string
  altText: string
  sectionKey?: string
  hasOverlay?: boolean
  className?: string
}

// Define positioning and styling for each section based on original images
const sectionStyles: Record<string, any> = {
  section2: {
    position: { top: '15%', left: '8%', transform: 'translate(0, 0)' },
    textAlign: 'left' as const,
    color: '#ffffff',
    textShadow: '2px 2px 4px rgba(0,0,0,0.7)',
    maxWidth: '45%'
  },
  section3: {
    position: { top: '20%', right: '8%', transform: 'translate(0, 0)' },
    textAlign: 'right' as const,
    color: '#2d3748',
    textShadow: '1px 1px 2px rgba(255,255,255,0.8)',
    maxWidth: '50%'
  },
  section4: {
    position: { top: '25%', left: '10%', transform: 'translate(0, 0)' },
    textAlign: 'left' as const,
    color: '#1a365d',
    textShadow: '1px 1px 3px rgba(255,255,255,0.9)',
    maxWidth: '45%'
  },
  section5: {
    position: { top: '20%', right: '5%', transform: 'translate(0, 0)' },
    textAlign: 'right' as const,
    color: '#ffffff',
    textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
    maxWidth: '50%'
  },
  section6: {
    position: { top: '30%', left: '50%', transform: 'translate(-50%, 0)' },
    textAlign: 'center' as const,
    color: '#ffffff',
    textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
    maxWidth: '60%'
  }
}

export default function ImageWithOverlay({ 
  imageSrc, 
  altText, 
  sectionKey, 
  hasOverlay = false,
  className = ""
}: ImageWithOverlayProps) {
  const { t } = useTranslation()

  if (!hasOverlay || !sectionKey) {
    return (
      <img 
        src={imageSrc} 
        alt={altText}
        className={className}
      />
    )
  }

  const styleConfig = sectionStyles[sectionKey] || sectionStyles.section6

  return (
    <div style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
      <img 
        src={imageSrc} 
        alt={altText}
        className={className}
        style={{ width: '100%', height: 'auto' }}
      />
      <div style={{
        position: 'absolute',
        ...styleConfig.position,
        textAlign: styleConfig.textAlign,
        color: styleConfig.color,
        textShadow: styleConfig.textShadow,
        padding: 'clamp(10px, 3vw, 20px)',
        maxWidth: styleConfig.maxWidth
      }}>
        <h2 style={{
          fontSize: 'clamp(1rem, 4vw, 2rem)',
          fontWeight: 'bold',
          marginBottom: 'clamp(4px, 1vw, 8px)',
          lineHeight: '1.1'
        }}>
          {t(`sections.${sectionKey}.title`)}
        </h2>
        <h3 style={{
          fontSize: 'clamp(0.8rem, 3vw, 1.2rem)',
          fontWeight: '600',
          marginBottom: 'clamp(6px, 1.5vw, 12px)',
          opacity: 0.9
        }}>
          {t(`sections.${sectionKey}.subtitle`)}
        </h3>
        <p style={{
          fontSize: 'clamp(0.7rem, 2.5vw, 0.95rem)',
          lineHeight: '1.4',
          opacity: 0.95
        }}>
          {t(`sections.${sectionKey}.description`)}
        </p>
      </div>
    </div>
  )
}