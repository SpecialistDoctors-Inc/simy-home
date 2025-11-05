"use client";

import React from 'react';

type Props = {
  onClick?: () => void;
  className?: string;
};

/**
 * Apple ログインボタン（クライアントコンポーネント）
 * - デフォルトでは no-op の onClick。実装時に onClick を渡してください。
 */
export default function AppleLoginButton({ onClick, className }: Props) {
  const handleClick = () => {
    if (onClick) return onClick();
    // TODO: Apple ログイン処理を実装
    if (process.env.NODE_ENV !== 'production') {
      console.log('Apple login clicked');
    }
  };

  return (
    <button
      onClick={handleClick}
      className={className}
      style={{
        background: '#000',
        color: '#fff',
        border: 'none',
        padding: '12px 24px',
        borderRadius: 6,
        margin: '12px 0',
        display: 'flex',
        alignItems: 'center',
        fontSize: 16,
        cursor: 'pointer',
        width: 260,
      }}
    >
      <img
        src="https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg"
        alt="Apple"
        style={{ width: 24, height: 24, marginRight: 12, filter: 'invert(1)' }}
      />
      Appleで続行
    </button>
  );
}
