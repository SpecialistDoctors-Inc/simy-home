'use client';

import Header from '@/components/Header';
import { useEffect, useRef } from 'react';

const APP_STORE_URL = 'https://apps.apple.com/jp/app/simy/id6745385262';
const APP_SCHEME = 'app.aimentor.auth://';

export default function RedirectPage() {
  const appOpenedRef = useRef(false);

  useEffect(() => {
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobile = /iphone|ipad|ipod|android/.test(userAgent);
    
    if (!isMobile) {
      return;
    }

    const checkAppOpened = () => {
      if (!appOpenedRef.current) {
        window.location.href = APP_STORE_URL;
      }
    };

    const markAppAsOpened = () => {
      appOpenedRef.current = true;
    };

    document.addEventListener('visibilitychange', markAppAsOpened);
    window.addEventListener('blur', markAppAsOpened);

    window.location.href = APP_SCHEME;

    const redirectTimeout = setTimeout(() => {
      document.removeEventListener('visibilitychange', markAppAsOpened);
      window.removeEventListener('blur', markAppAsOpened);
      checkAppOpened();
    }, 2000);

    return () => {
      clearTimeout(redirectTimeout);
      document.removeEventListener('visibilitychange', markAppAsOpened);
      window.removeEventListener('blur', markAppAsOpened);
    };
  }, []);

    return (
      <main>
        <Header />
        <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '100px 20px'
      }}>
        <div style={{
          maxWidth: '500px',
          width: '100%',
          background: 'white',
          borderRadius: '24px',
          padding: '48px 32px',
          textAlign: 'center',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
        }}>
          {/* タイトル */}
          <h1 style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#1a1a1a',
            marginBottom: '12px'
          }}>
            SIMY
          </h1>

          <p style={{
            fontSize: '16px',
            color: '#666',
            marginBottom: '40px'
          }}>
            スマートフォンでQRコードを<br />
            スキャンしてダウンロード
          </p>

          {/* QRコード */}
          <div style={{
            background: '#f8f9fa',
            padding: '24px',
            borderRadius: '16px',
            marginBottom: '32px',
            display: 'inline-block'
          }}>
            <img
              src="/img/qr.png"
              alt="App Store QRコード"
              style={{
                width: '240px',
                height: '240px',
                display: 'block'
              }}
            />
          </div>

          {/* ダウンロードボタン */}
          <a
            href={APP_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-block',
              background: 'black',
              color: 'white',
              padding: '16px 32px',
              borderRadius: '12px',
              textDecoration: 'none',
              fontSize: '16px',
              fontWeight: '600',
              transition: 'transform 0.2s, box-shadow 0.2s',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              width: '100%',
              maxWidth: '280px',
              boxSizing: 'border-box'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.25)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            }}
          >
            App Storeで開く
          </a>

          {/* アプリログインボタン */}
          <div style={{ marginTop: '16px' }}>
            <a
              href="/auth/app-login"
              style={{
                display: 'inline-block',
                background: 'transparent',
                color: '#667eea',
                padding: '16px 32px',
                borderRadius: '12px',
                textDecoration: 'none',
                fontSize: '16px',
                fontWeight: '600',
                border: '2px solid #667eea',
                transition: 'all 0.2s',
                width: '100%',
                maxWidth: '280px',
                boxSizing: 'border-box'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#667eea';
                e.currentTarget.style.color = 'white';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = '#667eea';
              }}
            >
              🔐 アプリでログイン
            </a>
          </div>

          {/* フッター情報 */}
          <p style={{
            fontSize: '14px',
            color: '#999',
            marginTop: '32px'
          }}>
            iPhone・iPad対応
          </p>
        </div>
      </div>
      </main>
    );
}
