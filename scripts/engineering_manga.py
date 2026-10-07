"""Japanese editorial manga entry; original artwork is framed, never rewritten."""
from html import escape

ASSET = '/assets/engineer-manga/release-crew-ja.webp'
# Pixel bounds of the supplied 1055 × 1491 artwork. CSS reveals each panel
# on narrow screens without duplicating, resampling, or changing its pixels.
PANELS = [
    (0, 79, 525, 322, '不具合の報告', '登録が２件入るという報告。リリースを控えたチームが異変に気づく。'),
    (527, 79, 528, 322, '本番前に止める', '登録失敗の報告も増える。「本番前に必ず止めるぞ」と調査を決める。'),
    (0, 403, 525, 322, '仲間と動き出す', '「SIMY！ 原因を調べて、修正とテストまで頼む！」「まずは再現します。」'),
    (527, 403, 528, 322, '原因を突き止める', '通信エラー後のリトライが重複し、同じリクエストが２回送信される原因を特定する。'),
    (0, 727, 525, 344, 'ユーザーのために判断する', '「失敗すると入力が消えます。残しますか？」「残す！ ユーザーの時間を無駄にさせない。」'),
    (527, 727, 528, 344, '修正だけで終わらせない', '修正、再テスト、別のAIによるレビュー。テスト結果とレビュー結果をチームで確認する。'),
    (0, 1073, 511, 342, '根拠を見て決める', '変更、テスト、レビュー、ユーザー体験、監視を確認。「よし、根拠はそろった。デプロイするぞ！」'),
    (513, 1073, 542, 342, '次の開発へ', 'デプロイを終え、チームで喜ぶ。「この失敗、次の開発に活かそうぜ！」「次は、もっと遠くへ行こう！」'),
]


def manga(lang):
    if lang != 'ja':
        from engineering_manga_locales import render
        return render(lang, PANELS)
    panels = []
    transcript = []
    for i, (x, y, w, h, title, description) in enumerate(PANELS, 1):
        style = f'aspect-ratio:{w}/{h};--image-width:{1055/w*100:.6f}%;--image-left:{-x/w*100:.6f}%;--image-top:{-y/h*100:.6f}%'
        panels.append(f'<li><p class="manga-panel-label"><span>{i:02}</span>{title}</p><div class="manga-panel" style="{style}"><img src="{ASSET}" width="1055" height="1491" alt="{escape(description)}" loading="lazy" decoding="async"></div></li>')
        transcript.append(f'<li><strong>{title}</strong><p>{escape(description)}</p></li>')
    chapters = [
        ('01 / DELIVERY LOOP', '頼んだ後の、確認とやり直しまで。', 'テストで問題が見つかったら、修正してもう一度確認。何度も「続きをやって」と頼む手間を減らします。', panels[:4]),
        ('02 / あなたの判断', '大事なことだけ、あなたが決める。', '「失敗したら、入力を残す？」使う人のための方針はあなたが決め、修正と確認を任せます。', panels[4:7]),
        ('03 / SQM', '一度の失敗を、次の安心に。', '例えば次に別のフォームを作るとき。「再送すると二重登録にならない？」前回の不具合をもとに、確認漏れを見つけます。', panels[7:]),
    ]
    chapter_html = ''.join(f'<article class="manga-chapter"><header><p class="eyebrow">{label}</p><h3>{title}</h3><p>{body}</p></header><ol class="manga-panels" aria-label="{title}">{"".join(images)}</ol></article>' for label, title, body, images in chapters)
    return f'''<section class="manga-story" id="manga" aria-labelledby="manga-title">
      <div class="frame">
        <div class="manga-intro"><div><p class="eyebrow">漫画でわかる SIMY</p><h2 id="manga-title">確認に追われる毎日から、<br>つくることに集中する毎日へ。</h2></div></div>
        <aside class="manga-prologue" aria-labelledby="manga-pain-title">
          <p class="eyebrow">AIに開発を任せた、その後。</p>
          <h3 id="manga-pain-title">こんなこと、起きていませんか？</h3>
          <ul class="manga-pains">
            <li><span>まだ途中なのに</span><strong>エラーが残ったまま、<br>止まってる。</strong><p>また「続けて」と頼む。</p></li>
            <li><span>完了って言ったのに</span><strong>動かしてみたら、<br>動かない。</strong><p>結局、自分で確かめ直す。</p></li>
            <li><span>前にも伝えたのに</span><strong>同じルール違反が、<br>また入ってる。</strong><p>同じ注意を繰り返す。</p></li>
          </ul>
          <details class="manga-sources"><summary>参考にした開発者の投稿</summary>
            <p>Redditなどの個人の体験談をもとに再構成しています。直接の引用や、SIMY利用者の声ではありません。</p>
            <ul>
              <li><a href="https://www.reddit.com/r/ClaudeAI/comments/1n262js/" target="_blank" rel="noopener">Reddit：エラーが残っていても作業を止めるという相談（英語・別タブ）</a></li>
              <li><a href="https://www.reddit.com/r/ClaudeAI/comments/1ma96ha/" target="_blank" rel="noopener">Reddit：動かないコードを正常と報告するという相談（英語・別タブ）</a></li>
              <li><a href="https://community.openai.com/t/why-does-codex-repeat-the-same-mistakes/1383615" target="_blank" rel="noopener">OpenAI Community：伝えた制約に繰り返し違反するという報告（英語・別タブ）</a></li>
            </ul>
          </details>
          <p class="manga-bridge">続きを促す。動作を確かめる。同じ失敗を防ぐ。<br><strong>その負担を減らすSIMYの使い方を、ひとつの不具合から見てみましょう。</strong></p>
        </aside>
        {chapter_html}
        <div class="manga-reading-tools"><p>漫画は利用イメージです。画面・機能は実際と異なります。公開は権限と承認に従います。</p><a href="{ASSET}" target="_blank" rel="noopener">原画を大きく読む（別タブ） <span aria-hidden="true">↗</span></a></div>
        <details class="manga-transcript"><summary>漫画を文章で読む</summary><ol>{''.join(transcript)}</ol></details>

      </div>
    </section>{mechanism()}'''


def mechanism():
    """Concrete source-screen details with numbered reading guides."""
    screens = [
        ('delivery', 1456, 1080, '01 / SIMYデスクトップアプリ：DELIVERY LOOP', 'チームのローカル作業も、ひとつの一覧で。',
         'SIMYデスクトップアプリで、自分とチームメンバーのローカル作業を一覧に。選んだスレッドの状況と残りの作業を確認できます。',
         [('チームの作業を見る', '誰が、どのAIで、何を進めているか。メンバーのローカル作業も一覧で確認。'),
          ('選んだスレッドの状況', '二重登録を防ぐ修正を終え、連打と再送のテストを進めている状態。'),
          ('残りを確認', '再送・連打のテストと、別のAIによるレビューへ。')],
         'SIMYデスクトップアプリの説明用画面。左に自分とチームメンバーのローカル作業一覧、右に選んだスレッドの状況と残りの作業を表示。'),
        ('rules', 1558, 1010, '02 / SQM（Web）：再発防止ルール', '「再送しても1件」を、次のコードの確認条件に。',
         '画面のボタン制御だけでなく、受付APIでの重複防止と回帰テストを確認します。',
         [('防ぎたいこと', '再送や連打で、同じ申込みが2件登録される。'),
          ('守る条件', '同じ申込みは1件として扱い、別の申込みは正常に登録する。'),
          ('コードとテストを確認', '識別キーによる重複防止、同時送信、別の申込みを誤って止めないことをチェック。')],
         '説明用の再発防止ルール。受付APIの重複防止と、再送・連打・同時送信の回帰テスト条件を表示。'),
        ('systems', 1558, 1009, '03 / SQM（Web）：確認する範囲', '申込み画面だけでなく、APIと保存処理まで。',
         '二重登録を防ぐには、画面から受付・保存までの関係を確認する必要があります。',
         [('確認範囲を判断', 'AIが提案した対象を確認してから、品質チェックの範囲へ反映。'),
          ('関連するコードを把握', '申込み画面、受付API、データ保存、受付メール、回帰テストの関係を見る。')],
         '説明用の申込み受付システム。画面、API、データ保存、通知、回帰テスト、共通の型を持つリポジトリの関係。'),
    ]
    rows = []
    for key, width, height, label, title, body, notes, alt in screens:
        url = '/assets/engineer-mechanism/delivery-team.webp' if key == 'delivery' else f'/assets/engineer-mechanism/{key}-application.webp'
        points = ''.join(f'<li><strong>{i}　{heading}</strong><p>{text}</p></li>' for i, (heading, text) in enumerate(notes, 1))
        caveat = '<p class="mechanism-note">ルールの設定例です。実際の検出・テスト結果ではありません。</p>' if key == 'rules' else ''
        rows.append(f'<article class="mechanism-row"><div class="mechanism-copy"><p class="eyebrow">{label}</p><h3>{title}</h3><p>{body}</p></div><a class="mechanism-image" href="{url}" target="_blank" rel="noopener" aria-label="{title} 画面を拡大（別タブ）"><img src="{url}" width="{width}" height="{height}" alt="{alt}" loading="lazy" decoding="async"><span>画面を拡大 ↗</span></a><ol class="mechanism-points">{points}</ol>{caveat}</article>')
    return f'<section class="manga-mechanism" id="mechanism" aria-labelledby="mechanism-title"><div class="frame"><header><p class="eyebrow">申込みフォームの例で見る、SIMYのしくみ</p><h2 id="mechanism-title">何を見て、どう確かめるのか。</h2><p class="mechanism-note">実際の画面構成をもとに、漫画と同じ申込みフォームの事例へ内容を置き換えています（説明用の編集画像）。</p></header>{"".join(rows)}</div></section>'
