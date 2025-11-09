"use client";

import React, { useEffect, useState } from 'react';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';
import AppleLoginButton from '@/components/auth/AppleLoginButton';
import Header from '@/components/Header';
import MyPageContent from '@/components/mypage/MyPageContent';
import { createClient } from '@/utils/supabase/client';
import { User } from '@supabase/supabase-js';

/**
 * ログイン/設定統合ページ
 */
export default function Login() {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const supabase = createClient();

        // 現在のユーザーセッションを取得
        const getUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            setUser(user);
            setLoading(false);
        };

        getUser();

        // 認証状態の変更を監視
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => {
            subscription.unsubscribe();
        };
    }, []);

    const handleLogout = async () => {
        setUser(null);
    };

    if (loading) {
        return (
            <main>
                <Header />
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 120 }}>
                    <div>読み込み中...</div>
                </div>
            </main>
        );
    }

    // ログイン済みの場合はMyPageコンテンツを表示
    if (user) {
        return (
            <main>
                <Header showInstallButton={true} />
                <MyPageContent user={user} onLogout={handleLogout} />
            </main>
        );
    }

    // 未ログインの場合はログインボタンを表示
    return (
        <main>
            <Header />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 120 }}>
                <h2 style={{ marginBottom: 40 }}>Login / Sign Up</h2>
                <GoogleLoginButton />
                <AppleLoginButton />
            </div>
        </main>
    );
}
