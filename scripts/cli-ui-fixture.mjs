// A presentation-only dataset for native screenshots. No user files, host,
// credentials, provider execution, or network connections are used.
import { pathToFileURL } from 'node:url';
import { readFile } from 'node:fs/promises';

const entry = pathToFileURL(process.argv[2]);
const { createFixtureBackend } = await import(new URL('./desktop/fixture-backend.js', entry));
const { createDesktopServer } = await import(new URL('./desktop/server.js', entry));
const { version } = JSON.parse(await readFile(new URL('../package.json', entry), 'utf8'));
const built = createFixtureBackend({ state: 'ok' });
if (!built.ok) throw new Error(built.message);
const original = built.value;
// Translate sample content only; native UI strings come from the app itself.
const copy = new Map(Object.entries({
  'Add CSV export to the members page': '会員一覧にCSV出力を追加する',
  'Fix the flaky login end-to-end test': 'ログインのE2Eテストを安定させる',
  'Upgrade Next.js to 16': 'Next.jsを16に更新する',
  'Include archived members in the export?': 'アーカイブ済みの会員も出力しますか？',
  '212 archived. Including them adds a status column.': '対象は212件。含める場合は、状態を示す列を追加します。',
  'Include': '含める', 'Exclude': '含めない',
  'Reused the existing CSV helper': '既存のCSV出力処理を再利用',
  'File name is members-YYYY-MM-DD.csv': 'ファイル名は members-YYYY-MM-DD.csv',
  "Kept the test's current assertions": '既存のテストの確認項目を維持',
  'No fixed waits remain in the test': '固定時間の待機をテストから除去',
  'Login test passes 20 times in a row': 'ログインテストが20回連続で成功する',
  'grep: 0 matches': '固定時間の待機：0件',
  'Re-running the suite 20 times to make sure it holds.': '安定して動くか、テストを20回実行して確認しています。',
  'Missing index on a new column. Retry loop with no upper bound.': '新しい列のインデックス不足と、再試行の上限がない箇所を検出。',
  'Agent fixed both, check passed, PR opened.': '両方を修正し、再チェックに合格。PRを作成。',
}));
function localize(value) {
  if (typeof value === 'string') return copy.get(value) ?? value;
  if (Array.isArray(value)) return value.map(localize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v]) => [k,localize(v)]));
  return value;
}
const backend = {
  ...original,
  current() {
    const model = localize(original.current());
    // The upstream sample pins a 0.7 version. Use the actual release metadata
    // so it cannot be mistaken for the version whose UI is being captured.
    model.system.version = version;
    model.system.links.codex.version = 'v0.158.0';
    return model;
  },
};
const server = createDesktopServer({ backend });
const channel = server.attach({ input: process.stdin, output: process.stdout });
await channel.closed;
server.close();
original.close();
