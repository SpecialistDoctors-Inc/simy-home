"use client";

import { createClient } from '@/utils/supabase/client';
import React from 'react';

type Props = {
  className?: string;
};

/**
 * Apple ログインボタン（クライアントコンポーネント）
 */
export default function AppleLoginButton({ className }: Props) {
  const handleClick = async () => {
    const supabase = createClient();
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'apple',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
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
        justifyContent: 'center',
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
