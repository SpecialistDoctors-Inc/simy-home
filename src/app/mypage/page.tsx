"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient as createSupabaseClient } from "@/utils/supabase/client";
import MonthlyLimit from "@/components/mypage/MonthlyLimit";
import UsageDisplay from "@/components/mypage/UsageDisplay";
import PaymentMethod from "@/components/mypage/PaymentMethod";
import GoogleLoginButton from "@/components/auth/GoogleLoginButton";
import AppleLoginButton from "@/components/auth/AppleLoginButton";
import "./mypage.css";
import Header from "@/components/Header";

export default function MyPage() {
    // Mock user data for development
    const mockUser: User = {
        id: "12345678-1234-1234-1234-123456789abc",
        email: "user@example.com",
        app_metadata: {},
        user_metadata: {},
        aud: "authenticated",
        created_at: new Date().toISOString(),
    } as User;

    const [user, setUser] = useState<User | null>(mockUser);
    const [loading, setLoading] = useState(false);
    const [monthlyLimit, setMonthlyLimit] = useState(100);

    // Mock data - replace with actual data from your backend
    const currentUsage = 48; // Example: $48 used
    const effectiveDate = "May 1";

    useEffect(() => {
        const supabase = createSupabaseClient();
        // const getUser = async () => {
        //     const { data, error } = await supabase.auth.getUser();
        //     if (error) {
        //         setUser(null);
        //     } else {
        //         setUser(data.user);
        //     }
        //     setLoading(false);
        // };
        // getUser();
    }, []);

    const handleLimitChange = (newLimit: number) => {
        setMonthlyLimit(newLimit);
        // TODO: Save to backend
        console.log("New limit:", newLimit);
    };

    const handleLogout = async () => {
        try {
            const supabase = createSupabaseClient();
            await supabase.auth.signOut();
        } catch (e) {
            // no-op
        } finally {
            setUser(null);
            // 任意: ホームへ戻す
            if (typeof window !== 'undefined') {
                window.location.href = '/';
            }
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div>Loading...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="error-container">
                <div style={{ fontSize: 18, fontWeight: 600 }}>Please log in to view your page.</div>
                <GoogleLoginButton />
                <AppleLoginButton />
            </div>
        );
    }

    return (
          <main>
            <Header />
            <div className="mypage-container">
                <div className="mypage-header">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 , paddingTop: 80}}>
                        <h1 className="mypage-title">マイページ</h1>
                        <button className="logout-btn" onClick={handleLogout}>ログアウト</button>
                    </div>
                    <p className="user-info">
                        <strong>メールアドレス:</strong> {user.email}
                    </p>
                    <p className="user-info">
                        <strong>ID:</strong> {user.id}
                    </p>
                </div>

                <MonthlyLimit 
                    defaultLimit={monthlyLimit} 
                    onLimitChange={handleLimitChange}
                />

                <UsageDisplay 
                    currentUsage={currentUsage}
                    limit={monthlyLimit}
                    effectiveDate={effectiveDate}
                />

                <PaymentMethod
                    provider="stripe"
                />
            </div>
        </main>
    );
}