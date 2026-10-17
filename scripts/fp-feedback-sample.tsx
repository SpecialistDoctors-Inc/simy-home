import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StatusPill } from "@/components/ui/status-pill";

type State = "done" | "partial" | "not_done" | "unverified";
const labels: Record<State, string> = {
  done: "実施",
  partial: "一部実施",
  not_done: "未実施",
  unverified: "未確認",
};
const variants = {
  done: "success",
  partial: "warning",
  not_done: "danger",
  unverified: "neutral",
} as const;
const key = "simy-fp-feedback-sample-v1";
const states: State[] = [
  "done",
  "done",
  "partial",
  "done",
  "partial",
  "not_done",
  "partial",
  "not_done",
  "unverified",
  "done",
  "not_done",
  "unverified",
];
const tasks = [
  "前回の宿題を確認する",
  "選択肢と選ぶ理由を確認する",
  "次回の確認内容と日程を決める",
];
const initial = states.map((status, i) => ({
  id: `feedback-${i}`,
  advisor: `担当${"ABCD"[Math.floor(i / 3)]}（架空）`,
  task: tasks[i % 3],
  status,
  instruction: [
    "次の面談の冒頭で、前回お願いした資料がそろったか確認してください。",
    "比較する範囲を説明し、本人が何を基準に選びたいか聞いてください。",
    "次回までに誰が何を確認するかと、次回日程を一緒に確認してください。",
  ][i % 3],
  evidence:
    status === "unverified"
      ? ""
      : status === "not_done"
        ? "宿題や次回の確認に進まず、この面談は終了した。（架空記録）"
        : status === "partial"
          ? "話題にはしたが、具体的な確認内容までは合意していない。（架空記録）"
          : "お願いした内容を確認し、次に確認することを一緒に整理した。（架空記録）",
  reply:
    status === "done"
      ? "何を確認すればよいか分かりました。まだ迷っている点もあります。（架空の返答）"
      : "本人の理解・納得は引き続き確認する。",
}));
function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (
      Array.isArray(saved) &&
      saved.length === initial.length &&
      saved.every(
        (r, i) =>
          r.id === initial[i].id &&
          r.status in labels &&
          typeof r.evidence === "string" &&
          typeof r.reply === "string",
      )
    )
      return initial.map((r, i) => ({
        ...r,
        status: saved[i].status as State,
        evidence: saved[i].evidence as string,
        reply: saved[i].reply as string,
      }));
  } catch {
    /* Invalid sample data falls back to the fixed fictional examples. */
  }
  return initial;
}
export function SampleFeedbackReview() {
  const [rows, setRows] = useState(load);
  const [advisor, setAdvisor] = useState("all");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    status: "unverified" as State,
    evidence: "",
    reply: "",
  });
  const [message, setMessage] = useState("");
  const selectedRows = rows.filter(
    (r) => advisor === "all" || r.advisor === advisor,
  );
  const verified = selectedRows.filter((r) => r.status !== "unverified");
  const count = (s: State) => selectedRows.filter((r) => r.status === s).length;
  const rate = (n: number, denominator = verified.length) =>
    denominator ? `${((n / denominator) * 100).toFixed(1)}%` : "—";
  function save() {
    if (draft.status !== "unverified" && !draft.evidence.trim()) {
      setMessage(
        "実施・一部実施・未実施の判断には次の面談記録の根拠を入力してください。",
      );
      return;
    }
    const next = rows.map((r) => (r.id === selected ? { ...r, ...draft } : r));
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setRows(next);
      setSelected(null);
      setMessage("このブラウザーに保存しました。");
    } catch {
      setMessage("保存できませんでした。入力を保持しています。");
    }
  }
  return (
    <Card className="space-y-4 p-4" data-testid="feedback-implementation">
      <h3 className="text-card-title font-semibold">
        依頼した支援は、次の面談で実施されたか
      </h3>
      <p className="prose-jp text-sm text-muted-foreground">
        担当者別に、依頼した項目と次の面談記録を照合します。話題にしただけの場合は「一部実施」、記録がない場合は「未確認」です。実施と顧客の理解・納得は別々に確認します。
      </p>
      <p className="text-xs text-muted-foreground">
        架空の担当者4名・依頼12項目の体験例。実在の担当者やソニー生命の実績ではありません。保存先はこのブラウザー内です。
      </p>
      <label className="block text-sm">
        支援実施率の担当者
        <select
          className="mt-1 block h-10 w-full rounded-md border border-border bg-card px-3"
          aria-label="支援実施率の担当者"
          value={advisor}
          onChange={(e) => {
            setAdvisor(e.target.value);
            setSelected(null);
          }}
        >
          <option value="all">すべての担当者</option>
          {[...new Set(rows.map((r) => r.advisor))].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(Object.keys(labels) as State[]).map((s) => (
          <div key={s} className="rounded-md bg-secondary p-3">
            <StatusPill variant={variants[s]}>{labels[s]}</StatusPill>
            <p className="mt-2 text-section font-semibold tabular-nums">
              {s === "unverified" ? `${count(s)}項目` : rate(count(s))}
            </p>
            <p className="text-xs text-muted-foreground tabular-nums">
              {count(s)}項目
              {s === "unverified"
                ? "・率の分母から除外"
                : ` / 判定済み${verified.length}項目`}
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground tabular-nums">
        対象{selectedRows.length}項目・判定済み{verified.length}
        項目。一部実施まで含めた率 {rate(count("done") + count("partial"))}
        。人数率ではなく、依頼項目を分母にした率です。
      </p>
      <div className="overflow-x-auto">
        <table className="w-full whitespace-nowrap text-left text-row">
          <caption className="sr-only">架空の担当者別の依頼項目実施率</caption>
          <thead>
            <tr className="border-b border-border">
              <th className="p-2">担当者</th>
              <th className="p-2">実施</th>
              <th className="p-2">一部実施</th>
              <th className="p-2">未実施</th>
              <th className="p-2">未確認</th>
            </tr>
          </thead>
          <tbody>
            {[...new Set(selectedRows.map((r) => r.advisor))].map((name) => {
              const group = selectedRows.filter((r) => r.advisor === name);
              const n = group.filter((r) => r.status !== "unverified").length;
              return (
                <tr key={name} className="border-b border-border-subtle">
                  <th className="p-2 font-medium">{name}</th>
                  {(["done", "partial", "not_done"] as State[]).map((s) => {
                    const c = group.filter((r) => r.status === s).length;
                    return (
                      <td className="p-2 tabular-nums" key={s}>
                        {rate(c, n)}
                        <span className="block text-xs text-muted-foreground">
                          {c}/{n}項目
                        </span>
                      </td>
                    );
                  })}
                  <td className="p-2 tabular-nums">{group.length - n}項目</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <label className="block text-sm">
        支援実施の状態
        <select
          className="mt-1 block h-10 w-full rounded-md border border-border bg-card px-3"
          aria-label="支援実施の状態"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">すべての状態</option>
          {(Object.keys(labels) as State[]).map((s) => (
            <option key={s} value={s}>
              {labels[s]}
            </option>
          ))}
        </select>
      </label>
      <div className="divide-y divide-border-subtle">
        {selectedRows
          .filter((r) => filter === "all" || r.status === filter)
          .map((r) => (
            <div key={r.id} className="space-y-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-row font-medium">
                    {r.advisor} · {r.task}
                  </p>
                  <StatusPill variant={variants[r.status]}>
                    {labels[r.status]}
                  </StatusPill>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelected(selected === r.id ? null : r.id);
                    setDraft({
                      status: r.status,
                      evidence: r.evidence,
                      reply: r.reply,
                    });
                    setMessage("");
                  }}
                >
                  依頼と次の面談を確認
                </Button>
              </div>
              {selected === r.id && (
                <div
                  className="space-y-3 rounded-md bg-secondary p-4"
                  data-testid="feedback-evidence"
                >
                  <p className="text-sm font-semibold">
                    前の面談後の依頼 → 次の別面談での確認（架空）
                  </p>
                  <p className="prose-jp text-sm">{r.instruction}</p>
                  <label className="block text-sm">
                    実施の判断
                    <select
                      className="mt-1 block h-10 w-full rounded-md border border-border bg-card px-3"
                      aria-label="実施の判断"
                      value={draft.status}
                      onChange={(e) =>
                        setDraft({ ...draft, status: e.target.value as State })
                      }
                    >
                      {(Object.keys(labels) as State[]).map((s) => (
                        <option key={s} value={s}>
                          {labels[s]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm">
                    次の面談記録の根拠
                    <Input
                      className="mt-1"
                      value={draft.evidence}
                      onChange={(e) =>
                        setDraft({ ...draft, evidence: e.target.value })
                      }
                    />
                  </label>
                  <label className="block text-sm">
                    顧客の返答・残る不安
                    <Input
                      className="mt-1"
                      value={draft.reply}
                      onChange={(e) =>
                        setDraft({ ...draft, reply: e.target.value })
                      }
                    />
                  </label>
                  <Button onClick={save}>実施確認をこのブラウザーに保存</Button>
                </div>
              )}
            </div>
          ))}
      </div>
      {message && (
        <p role="status" className="prose-jp text-sm">
          {message}
        </p>
      )}
    </Card>
  );
}
