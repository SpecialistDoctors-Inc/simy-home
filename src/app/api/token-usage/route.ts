import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

type LlmTokenUsageRow = {
  id: string;
  user_id: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  created_at: string;
};

export type TokenUsageMetrics = {
  requestCount: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  latestUsageAt: string | null;
};

function createAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  );
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get("user_id");

  if (!userId) {
    return NextResponse.json({ error: "user_id is required" }, { status: 400 });
  }

  try {
    const supabase = createAdminClient();

    const { data, error } = await supabase
      .from("llm_token_usage")
      .select("prompt_tokens, completion_tokens, total_tokens, created_at")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .returns<Pick<LlmTokenUsageRow, "prompt_tokens" | "completion_tokens" | "total_tokens" | "created_at">[]>();

    if (error) {
      console.error("Error fetching llm_token_usage:", error);
      return NextResponse.json(
        { error: "Failed to fetch token usage" },
        { status: 500 }
      );
    }

    if (!data || data.length === 0) {
      const metrics: TokenUsageMetrics = {
        requestCount: 0,
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
        latestUsageAt: null,
      };
      return NextResponse.json(metrics);
    }

    const metrics: TokenUsageMetrics = {
      requestCount: data.length,
      promptTokens: data.reduce((sum, row) => sum + (row.prompt_tokens ?? 0), 0),
      completionTokens: data.reduce(
        (sum, row) => sum + (row.completion_tokens ?? 0),
        0
      ),
      totalTokens: data.reduce((sum, row) => sum + (row.total_tokens ?? 0), 0),
      latestUsageAt: data[0]?.created_at ?? null,
    };

    return NextResponse.json(metrics);
  } catch (e) {
    console.error("Unexpected error in token-usage route:", e);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
