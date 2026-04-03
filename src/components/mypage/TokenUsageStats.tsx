"use client";

import { useEffect, useState } from "react";
import type { TokenUsageMetrics } from "@/app/api/token-usage/route";

type Props = {
  userId: string;
};

type FetchState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "success"; data: TokenUsageMetrics };

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function TokenUsageStats({ userId }: Props) {
  const [state, setState] = useState<FetchState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function fetchUsage() {
      setState({ status: "loading" });
      try {
        const res = await fetch(`/api/token-usage?user_id=${encodeURIComponent(userId)}`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
        }
        const data: TokenUsageMetrics = await res.json();
        if (!cancelled) {
          if (data.requestCount === 0) {
            setState({ status: "empty" });
          } else {
            setState({ status: "success", data });
          }
        }
      } catch (e) {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Unknown error",
          });
        }
      }
    }

    fetchUsage();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  return (
    <div className="usage-display-card">
      <h3 className="usage-section-title">利用統計（トークン）</h3>

      {state.status === "loading" && (
        <div className="token-usage-loading">
          <div className="loading-spinner" />
          <span className="token-usage-loading-text">読み込み中…</span>
        </div>
      )}

      {state.status === "error" && (
        <div className="token-usage-error">
          <span className="token-usage-error-icon">⚠</span>
          <span className="token-usage-error-text">
            データの取得に失敗しました: {state.message}
          </span>
        </div>
      )}

      {state.status === "empty" && (
        <div className="token-usage-empty">
          <span className="token-usage-empty-text">
            まだ利用記録がありません。
          </span>
        </div>
      )}

      {state.status === "success" && (
        <div className="token-usage-grid">
          <div className="token-usage-item">
            <span className="token-usage-label">リクエスト数</span>
            <span className="token-usage-value">
              {formatNumber(state.data.requestCount)}
            </span>
          </div>
          <div className="token-usage-item">
            <span className="token-usage-label">プロンプトトークン</span>
            <span className="token-usage-value">
              {formatNumber(state.data.promptTokens)}
            </span>
          </div>
          <div className="token-usage-item">
            <span className="token-usage-label">補完トークン</span>
            <span className="token-usage-value">
              {formatNumber(state.data.completionTokens)}
            </span>
          </div>
          <div className="token-usage-item">
            <span className="token-usage-label">合計トークン</span>
            <span className="token-usage-value token-usage-total">
              {formatNumber(state.data.totalTokens)}
            </span>
          </div>
          <div className="token-usage-item token-usage-item--full">
            <span className="token-usage-label">最終利用日時</span>
            <span className="token-usage-value">
              {formatTimestamp(state.data.latestUsageAt)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
