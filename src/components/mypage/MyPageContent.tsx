"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient as createSupabaseClient } from "@/utils/supabase/client";
import SimyLaunchSection from "@/components/mypage/SimyLaunchSection";
import NextSteps from "@/components/mypage/NextSteps";
import MonthlyLimit from "@/components/mypage/MonthlyLimit";
import UsageDisplay from "@/components/mypage/UsageDisplay";
import PaymentMethod from "@/components/mypage/PaymentMethod";
import ServiceStatus from "@/components/mypage/ServiceStatus";
import "./mypage.css";

type Props = {
  user: User;
  onLogout?: () => void;
};

// DB・user_settingsの全カラム
type UserSettingsRow = {
  id: string; // uuid (auth.users.id と一致)
  monthly_limit_amount: number | null; // numeric
  monthly_limit_currency: string | null; // text
  current_month_usage: number | null; // numeric
  usage_reset_date: string | null; // timestamptz
  is_active: boolean | null; // boolean
  created_at: string | null; // timestamptz
  updated_at: string | null; // timestamptz
};

/**
 * MyPageのメインコンテンツコンポーネント
 * ログイン済みユーザーの情報、使用量、決済方法を表示
 */
export default function MyPageContent({ user, onLogout }: Props) {
  // 取得失敗時は現在のPGのデフォルト値(現状はコンポーネントのデフォルトと同義)をそのまま使う
  const [monthlyLimit, setMonthlyLimit] = useState<number>(0);
  const [currentUsage, setCurrentUsage] = useState<number>(0);
  const [effectiveDate, setEffectiveDate] = useState<string>("");
  
  // Payment method states
  const [hasPaymentMethod, setHasPaymentMethod] = useState(false);
  const [customerInfo, setCustomerInfo] = useState<{
    customerId?: string;
    last4?: string;
    brand?: string;
  }>({});
  
  // Service active state
  const [isActive, setIsActive] = useState(true);
  const [isUpdatingActive, setIsUpdatingActive] = useState(false);
  
  // Loading state
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const fetchUserSettings = async () => {
      try {
        const supabase = createSupabaseClient();
        const { data, error } = await supabase
          .from("user_settings")
          .select("*")
          .eq("id", user.id)
          .maybeSingle<UserSettingsRow>();

        if (error) throw error;
        // 行が無いならエラーにする
        if (!data) {
          throw new Error(`No user_settings found for user.id = ${user.id}`);
        }

        if (typeof data.monthly_limit_amount === "number") {
          setMonthlyLimit(data.monthly_limit_amount);
        }
        if (typeof data.current_month_usage === "number") {
          setCurrentUsage(data.current_month_usage);
        }
        if (data.usage_reset_date) {
          const d = new Date(data.usage_reset_date);
          const formatted = new Intl.DateTimeFormat("ja-JP", {
            year: "numeric",
            month: "long",
            day: "numeric",
          }).format(d);
          setEffectiveDate(formatted);
        } else {
          setEffectiveDate("");
        }
        if (typeof data.is_active === "boolean") {
          setIsActive(data.is_active);
        }
      } catch (e) {
        console.error("Error fetching user_settings:", e);
      }
    };

    const loadPaymentMethodInfo = async () => {
      try {
        const supabase = createSupabaseClient();

        const { data, error } = await supabase.functions.invoke(
          "stripe-get-customer?user_id=" + user.id,
          {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          }
        );

        if (error || !data) {
          setHasPaymentMethod(false);
          setCustomerInfo({});

          const { data: createData, error: createError } =
            await supabase.functions.invoke("stripe-create-customer", {
              body: {
                user_id: user.id,
              },
            });
          if (createError) {
            console.error("Error creating Stripe customer:", createError);
          }
          return;
        }

        // レスポンスの構造を整形
        const responseData = data as {
          ok?: boolean;
          customer?: { id: string };
          payment_method?: { last4?: string; brand?: string };
        };

        const customerId = responseData.customer?.id;
        const last4 = responseData.payment_method?.last4;
        const brand = responseData.payment_method?.brand;

        if (customerId && last4 && brand) {
          setHasPaymentMethod(true);
          setCustomerInfo({ customerId, last4, brand });
        } else {
          setHasPaymentMethod(false);
          setCustomerInfo({});

          const { data: createData, error: createError } =
            await supabase.functions.invoke("stripe-create-customer", {
              body: {
                user_id: user.id,
              },
            });
          if (createError) {
            console.error("Error creating Stripe customer:", createError);
          }
        }
      } catch (error) {
        console.error("Error loading payment method info:", error);
      }
    };

    const loadData = async () => {
      await Promise.all([fetchUserSettings(), loadPaymentMethodInfo()]);
      setIsLoading(false);
    };
    
    loadData();
  }, [user.id]);

  const handleLimitChange = async (newLimit: number) => {
    setMonthlyLimit(newLimit);
    try {
      const supabase = createSupabaseClient();

      // idの存在確認（存在しない場合はエラー）
      const { data: existing, error: selectError } = await supabase
        .from("user_settings")
        .select("id")
        .eq("id", user.id)
        .maybeSingle();

      if (selectError) throw selectError;
      if (!existing) {
        throw new Error(
          `No existing user_settings row found for id = ${user.id}`
        );
      }

      const { error: updateError } = await supabase
        .from("user_settings")
        .update({
          monthly_limit_amount: newLimit,
          updated_at: new Date().toISOString(),
        })
        .eq("id", user.id);

      if (updateError) {
        console.error("Failed to update user_settings:", updateError.message);
      } 
    } catch (e) {
      console.error("Unexpected error in handleLimitChange:", e);
    }
  };

  const handleActiveToggle = async (newIsActive: boolean) => {
    setIsUpdatingActive(true);
    try {
      const supabase = createSupabaseClient();

      const { error: updateError } = await supabase
        .from("user_settings")
        .update({
          is_active: newIsActive,
          updated_at: new Date().toISOString(),
        })
        .eq("id", user.id);

      if (updateError) {
        console.error("Failed to update is_active:", updateError.message);
        alert("利用状態の更新に失敗しました。");
      } else {
        setIsActive(newIsActive);
      }
    } catch (e) {
      console.error("Unexpected error in handleActiveToggle:", e);
      alert("利用状態の更新に失敗しました。");
    } finally {
      setIsUpdatingActive(false);
    }
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
        <div className="mypage-header-top">
          <h1 className="mypage-title">マイページ</h1>
          <a
            href="/auth/app-login"
            className="btn app-login-btn"
            style={{
              display: 'inline-block',
              textAlign: 'center',
              textDecoration: 'none',
              background: '#667eea',
              color: 'white',
              border: '2px solid #667eea',
              padding: '8px 16px',
              fontSize: '14px',
              margin: 0,
              whiteSpace: 'nowrap'
            }}
          >
            🔐 アプリへログイン
          </a>
        </div>
        <p className="user-info">
          <strong>メールアドレス:</strong> {user.email}
        </p>
        <p className="user-info">
          <strong>ID:</strong> {user.id}
        </p>
      </div>

      {isLoading ? (
        <div className="loading-container">
          <div className="loading-spinner" />
        </div>
      ) : (
        <>
          {hasPaymentMethod? <></> : <SimyLaunchSection />}
          {hasPaymentMethod? <></> : <NextSteps hasPaymentMethod={hasPaymentMethod} userId={user.id} />}
          <MonthlyLimit
            isActive={isActive}
            defaultLimit={monthlyLimit}
            onLimitChange={handleLimitChange}
          />
          <UsageDisplay
            currentUsage={currentUsage}
            limit={monthlyLimit}
            effectiveDate={hasPaymentMethod ? effectiveDate : ""}
          />
          <PaymentMethod
            provider="stripe"
            hasPaymentMethod={hasPaymentMethod}
            customerInfo={customerInfo}
            userId={user.id}
          />
          <ServiceStatus
            isActive={isActive}
            isUpdating={isUpdatingActive}
            onToggle={handleActiveToggle}
          />

          <button className="logout-btn btn" onClick={handleLogout}>
            ログアウト
          </button>
        </>
      )}
    </div>
  );
}
