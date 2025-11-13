import fs from 'fs'
import path from 'path'
import { Metadata } from 'next'
import '../markdown.css'

export const metadata: Metadata = {
  title: 'Privacy Policy - SIMY',
  description: 'Privacy Policy for SIMY application',
}

export default function PrivacyPage() {
  const privacyPath = path.join(process.cwd(), 'src', 'app', 'privacy.md')
  const privacyContent = fs.readFileSync(privacyPath, 'utf8')

  return (
    <div className="markdown-container">
      <nav className="markdown-nav">
        <a href="/">Back to Home</a>
      </nav>
      <div 
        className="markdown-content"
        dangerouslySetInnerHTML={{ 
          __html: privacyContent
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^\*\*(.+?)\*\*/gm, '<strong>$1</strong>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*?<\/li>\s*)+/gs, '<ul>$&</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^([^<\n][^\n]*[^>\n])$/gm, '<p>$1</p>')
            .replace(/<p>(<h[1-6]>)/g, '$1')
            .replace(/(<\/h[1-6]>)<\/p>/g, '$1')
            .replace(/<p>(<ul>)/g, '$1')
            .replace(/(<\/ul>)<\/p>/g, '$1')
            .replace(/<p><\/p>/g, '')
        }}
      />
    </div>
  )
}