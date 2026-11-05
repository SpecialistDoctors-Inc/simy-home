import { App, applyDocumentTheme, applyHostStyleVariables } from '@modelcontextprotocol/ext-apps';
import { Card, type View } from './card';

const app = new App({ name: 'HP publication confirmation', version: '1.0.0' }, {}, { autoResize: true });
const element = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const confirm = element<HTMLButtonElement>('confirm');
const refresh = element<HTMLButtonElement>('refresh');
function link(id: string, url: string | null) {
  const anchor = element<HTMLAnchorElement>(id);
  anchor.hidden = !url;
  if (url) { anchor.href = url; anchor.textContent = url; }
  else anchor.removeAttribute('href');
}
function render(view: Readonly<View>) {
  element('site').textContent = view.site || 'ホームページの公開確認';
  element('summary').textContent = view.summary;
  element('status').textContent = view.message;
  element('status').dataset.phase = view.phase;
  element('operation').textContent = view.operationId ? `操作ID: ${view.operationId}` : '';
  element('expiry').textContent = view.expiresAt && view.phase === 'ready' ? `確認期限: ${new Date(view.expiresAt).toLocaleTimeString('ja-JP')}` : '';
  confirm.disabled = !view.connected || view.phase !== 'ready';
  confirm.textContent = view.phase === 'sending' ? '送信中…' : 'この内容の公開を依頼する';
  refresh.hidden = !view.operationId;
  refresh.disabled = !view.connected;
  link('preview', view.preview); link('production', view.production);
}
const card = new Card(app, render);
confirm.addEventListener('click', event => { void card.confirm(event.isTrusted); });
refresh.addEventListener('click', event => { void card.refresh(event.isTrusted); });
app.addEventListener('toolresult', result => card.receive(result));
app.addEventListener('toolcancelled', () => card.connect(false));
app.addEventListener('hostcontextchanged', context => {
  if (context.theme) applyDocumentTheme(context.theme);
  if (context.styles?.variables) applyHostStyleVariables(context.styles.variables);
});
// The host SDK owns postMessage validation and the app-only tool channel.
// A local trusted click is a UI guard, not a server-verifiable signature.
void app.connect().then(() => {
  const context = app.getHostContext();
  if (context?.theme) applyDocumentTheme(context.theme);
  if (context?.styles?.variables) applyHostStyleVariables(context.styles.variables);
  card.connect(true);
}).catch(() => {
  card.connect(false);
  element('status').textContent = '確認カードに接続できません。対応するアプリホストから開いてください。';
});
setInterval(() => card.tick(), 1000);
