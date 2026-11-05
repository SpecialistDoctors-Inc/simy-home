/** Local fake host: official AppBridge with fake operation receipts only. */
import { AppBridge, PostMessageTransport } from '@modelcontextprotocol/ext-apps/app-bridge';
const status = document.getElementById('host-status')!;
const calls = document.getElementById('calls')!;
const model = document.getElementById('model-context')!;
let bridge: AppBridge | null = null;
let mode = 'ready';
let count = 0;
const nonce = 'local-fake-private-card-nonce-1234567890';
const operationId = '22222222-2222-4222-8222-222222222222';
async function mount(nextMode: string) {
  mode = nextMode; count = 0; calls.textContent = 'なし'; model.textContent = 'なし'; status.textContent = '接続中';
  if (bridge) await bridge.close();
  const frame = document.createElement('iframe'); frame.id = 'card'; frame.title = '公開確認カード';
  document.getElementById('frame')!.replaceChildren(frame);
  bridge = new AppBridge(null, { name: 'Local fake host', version: '1.0.0' }, { serverTools: {}, updateModelContext: { text: {} } });
  bridge.oncalltool = async params => {
    count++; calls.textContent = `${count}件: ${params.name}`;
    if (params.name === 'hp_confirm_publish') {
      if (mode === 'rejected') return { isError: true, content: [{ type: 'text', text: 'confirmation_stale' }] };
      if (mode === 'ambiguous') throw new Error('Simulated ambiguous transport failure');
      if (params.arguments?.confirmation_nonce !== nonce) return { isError: true, content: [{ type: 'text', text: 'confirmation_invalid' }] };
      const reporting = ['reporting', 'needs_attention', 'published_after_cancel_or_revocation'].includes(mode);
      return { content: [], structuredContent: { operation_id: operationId, kind: 'publish', status: reporting ? mode : 'queued', ...(reporting ? { result: { kind: 'published', receipt: { verified: true } } } : {}) } };
    }
    if (params.name === 'hp_get_operation') return { content: [], structuredContent: { operation_id: operationId, kind: 'publish', status: 'completed' } };
    return { isError: true, content: [{ type: 'text', text: 'Unknown fake tool' }] };
  };
  bridge.onupdatemodelcontext = async params => { model.textContent = JSON.stringify(params); return {}; };
  bridge.oninitialized = async () => {
    status.textContent = '接続済み（ローカルの模擬ホスト）';
    await bridge!.sendToolInput({ arguments: { site_id: 'example-site', preview_id: '33333333-3333-4333-8333-333333333333' } });
    await bridge!.sendToolResult({ content: [], structuredContent: { approval_id: '11111111-1111-4111-8111-111111111111', site_name: 'サンプル医院', summary: '診療時間のお知らせを更新します。\nプレビューで文章・リンクをご確認ください。', preview_url: 'https://preview.example.invalid/current', production_url: 'https://site.example.invalid', expires_at: Math.floor(Date.now() / 1000) + (mode === 'expired' ? -1 : 600) }, _meta: mode === 'missing' ? {} : { confirmation_nonce: nonce } });
  };
  await bridge.connect(new PostMessageTransport(frame.contentWindow!, frame.contentWindow!));
  frame.src = '/publish.html';
}
document.querySelectorAll<HTMLButtonElement>('[data-mode]').forEach(button => button.addEventListener('click', () => { void mount(button.dataset.mode!); }));
document.getElementById('synthetic')!.addEventListener('click', () => {
  const frame = document.getElementById('card') as HTMLIFrameElement;
  (frame.contentDocument?.getElementById('confirm') as HTMLButtonElement)?.click();
});
void mount('ready');
