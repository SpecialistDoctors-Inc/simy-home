/** State machine with no provider calls, token access, or model-visible nonce. */
export type ToolResult = { isError?: boolean; structuredContent?: unknown; _meta?: Record<string, unknown> };
type Bridge = {
  callServerTool(params: { name: string; arguments: Record<string, string> }): Promise<ToolResult>;
  updateModelContext(params: { content: { type: 'text'; text: string }[] }): Promise<unknown>;
};
export type View = {
  mode: 'publish' | 'connection_test';
  phase: 'waiting' | 'ready' | 'sending' | 'queued' | 'completed' | 'error' | 'expired';
  message: string; site: string; summary: string; preview: string | null;
  production: string | null; expiresAt: number; operationId: string | null; connected: boolean;
};
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function publicHttps(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

function dataOf(result: ToolResult): Record<string, unknown> | undefined {
  const data = result.structuredContent;
  return data && typeof data === 'object' && !Array.isArray(data) ? data as Record<string, unknown> : undefined;
}

export class Card {
  private approval: string | null = null;
  private nonce: string | null = null;
  private attempted = false;
  private polling = false;
  readonly view: View = { mode: 'publish', phase: 'waiting', message: '確認情報を待っています。', site: '', summary: '', preview: null, production: null, expiresAt: 0, operationId: null, connected: false };
  constructor(private bridge: Bridge, private render: (view: Readonly<View>) => void, private now = () => Date.now()) { this.paint(); }
  private paint() { this.render({ ...this.view }); }
  connect(connected: boolean) { this.view.connected = connected; this.paint(); }
  private error(message: string) { this.view.phase = 'error'; this.view.message = message; this.paint(); }
  receive(result: ToolResult) {
    const data = dataOf(result);
    // Confirmation/get-operation results are handled by their own awaited calls.
    if (!data || typeof data.approval_id !== 'string') {
      if (!this.attempted) { this.approval = null; this.nonce = null; this.error('確認情報を取得できませんでした。新しい確認カードを依頼してください。'); }
      return;
    }
    if (this.attempted && data.approval_id === this.approval) return;
    const nonce = result._meta?.confirmation_nonce;
    if (result.isError || !['publish', 'connection_test'].includes(String(data.mode)) || !uuid.test(data.approval_id) || typeof nonce !== 'string' || nonce.length < 32 || nonce.length > 256 || typeof data.expires_at !== 'number' || !Number.isFinite(data.expires_at) || typeof data.site_name !== 'string' || typeof data.summary !== 'string') {
      this.approval = null; this.nonce = null;
      this.error('必要な確認情報がありません。新しい確認カードを依頼してください。'); return;
    }
    this.approval = data.approval_id; this.nonce = nonce; this.attempted = false;
    Object.assign(this.view, { mode: data.mode, phase: 'ready', message: data.mode === 'connection_test' ? '接続テストです。公開は行いません。接続を確認してください。' : 'プレビューと公開先を確認してから、公開を依頼してください。', site: data.site_name, summary: data.summary, preview: publicHttps(data.preview_url), production: publicHttps(data.production_url), expiresAt: Math.min(data.expires_at * 1000, this.now() + 600000), operationId: null });
    if (!this.view.preview || !this.view.production) { this.nonce = null; this.error('安全なプレビューURLまたは公開先を確認できません。運用担当にお問い合わせください。'); return; }
    this.tick(); this.paint();
  }
  tick() {
    if (this.view.phase === 'ready' && this.view.expiresAt <= this.now()) {
      this.nonce = null; this.view.phase = 'expired'; this.view.message = '確認期限が切れました。新しい確認カードを依頼してください。'; this.paint();
    }
  }
  async confirm(trusted: boolean) {
    this.tick();
    if (!trusted || !this.view.connected || this.attempted || this.view.phase !== 'ready' || !this.approval || !this.nonce) return;
    this.attempted = true;
    const nonce = this.nonce, approval = this.approval, mode = this.view.mode; this.nonce = null;
    this.view.phase = 'sending'; this.view.message = this.view.mode === 'connection_test' ? '接続を確認しています…' : '公開依頼を送信しています…'; this.paint();
    try {
      const result = await this.bridge.callServerTool({ name: 'hp_confirm_publish', arguments: { approval_id: approval, confirmation_nonce: nonce } });
      // A replacement card owns the view; an older in-flight result must not repaint it.
      if (this.approval !== approval) return;
      if (result.isError) { this.error('確認は受け付けられませんでした。状態を確認し、新しい確認カードを依頼してください。'); return; }
      // The server's immutable test mode cannot create a publication request,
      // including when the response is lost or publication is later enabled.
      if (mode === 'connection_test') {
        const data = dataOf(result);
        if (data?.kind !== 'connection_test' || data.status !== 'completed' || data.approval_id !== approval) {
          this.error('接続確認の結果を確認できません。公開は依頼していません。'); return;
        }
        this.view.phase = 'completed'; this.view.message = '接続を確認しました。公開は行っていません。'; this.paint();
        return;
      }
      this.operation(result);
      if (this.view.operationId) {
        // Keep approval IDs, private nonce, provider data and copy out of model context.
        try { await this.bridge.updateModelContext({ content: [{ type: 'text', text: JSON.stringify({ operation_id: this.view.operationId }) }] }); }
        catch { /* The operation receipt remains available on the card. Never resend confirmation. */ }
      }
    } catch { if (this.approval !== approval) return; this.error(mode === 'connection_test' ? '接続確認の結果を取得できません。公開は依頼していません。新しい確認カードを依頼してください。' : '送信結果を確認できません。再送せず、会話から操作状況の確認を依頼してください。'); }
  }
  private operation(result: ToolResult) {
    const data = dataOf(result);
    if (!data || typeof data.operation_id !== 'string' || !uuid.test(data.operation_id) || data.kind !== 'publish' || !['queued', 'running', 'completed', 'failed', 'cancelled', 'retry_wait', 'reconciling', 'needs_attention', 'reporting', 'published_after_cancel_or_revocation'].includes(String(data.status))) {
      this.error('公開依頼の状態を確認できません。再送せず、運用担当にお問い合わせください。'); return;
    }
    this.view.operationId = data.operation_id;
    const outcome = data.result && typeof data.result === 'object' ? data.result as Record<string, unknown> : {};
    const receipt = outcome.receipt && typeof outcome.receipt === 'object' ? outcome.receipt as Record<string, unknown> : {};
    const published = ['published', 'published_after_cancel_or_revocation'].includes(String(outcome.kind)) && receipt.verified === true;
    if (data.status === 'published_after_cancel_or_revocation') { this.view.phase = 'error'; this.view.message = 'キャンセルまたは権限変更後に、公開済みの状態が確認されました。公開先を確認し、運用担当にお問い合わせください。'; }
    else if (data.status === 'needs_attention') { this.view.phase = 'error'; this.view.message = published ? '公開は完了しましたが、結果の記録・通知に確認が必要です。運用担当にお問い合わせください。公開依頼は再送しないでください。' : '公開処理の確認が必要です。公開完了は確認できていません。再送せず、運用担当にお問い合わせください。'; }
    else if (data.status === 'reporting' || (published && data.status === 'reconciling')) { this.view.phase = 'queued'; this.view.message = published ? '公開は完了しました。結果の記録・通知を確認しています。' : '処理結果を確認しています。公開完了はまだ確認できていません。'; }
    else if (data.status === 'completed') { this.view.phase = 'completed'; this.view.message = data.reporting_state === 'suppressed' ? '公開処理は完了しました。結果の通知は送信されていません。公開先の表示をご確認ください。' : '公開処理が完了しました。公開先の表示をご確認ください。'; }
    else if (data.status === 'failed' || data.status === 'cancelled') { this.view.phase = 'error'; this.view.message = data.status === 'failed' ? '公開処理に失敗しました。運用担当にお問い合わせください。' : '公開依頼はキャンセルされました。'; }
    else { this.view.phase = 'queued'; this.view.message = data.status === 'running' ? '公開処理中です。まだ完了していません。' : data.status === 'retry_wait' ? '処理の再開を待っています。まだ公開完了は確認できていません。' : data.status === 'reconciling' ? '操作結果を照合しています。公開完了は未確認です。公開依頼は再送しないでください。' : '公開依頼を受け付けました。まだ公開は完了していません。'; }
    this.paint();
  }
  async refresh(trusted: boolean) {
    if (!trusted || !this.view.connected || !this.view.operationId || this.polling) return;
    this.polling = true;
    const approval = this.approval, operation = this.view.operationId;
    try {
      const result = await this.bridge.callServerTool({ name: 'hp_get_operation', arguments: { operation_id: operation } });
      if (this.approval !== approval || this.view.operationId !== operation) return;
      if (result.isError) this.error('現在の操作状況を取得できません。公開依頼は再送しないでください。');
      else this.operation(result);
    } catch { if (this.approval !== approval || this.view.operationId !== operation) return; this.error('現在の操作状況を取得できません。公開依頼は再送しないでください。'); }
    finally { this.polling = false; }
  }
}
