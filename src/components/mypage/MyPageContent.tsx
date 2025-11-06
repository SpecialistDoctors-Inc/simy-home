"use client";

import { useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient as createSupabaseClient } from "@/utils/supabase/client";
import MonthlyLimit from "@/components/mypage/MonthlyLimit";
import UsageDisplay from "@/components/mypage/UsageDisplay";
import PaymentMethod from "@/components/mypage/PaymentMethod";
import "./mypage.css";

type Props = {
  user: User;
  onLogout?: () => void;
};

/**
 * MyPageのメインコンテンツコンポーネント
 * ログイン済みユーザーの情報、使用量、決済方法を表示
 */
export default function MyPageContent({ user, onLogout }: Props) {
  const [monthlyLimit, setMonthlyLimit] = useState(100);

  // Mock data - replace with actual data from your backend
  const currentUsage = 48; // Example: $48 used
  const effectiveDate = "May 1";

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
      if (onLogout) {
        onLogout();
      }
    }
  };

  return (
    <div className="mypage-container">
      <div className="mypage-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, paddingTop: 80 }}>
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
  );
}
