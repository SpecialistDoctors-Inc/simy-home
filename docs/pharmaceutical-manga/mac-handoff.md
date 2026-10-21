# Macでの制作再開

> 2026-10-21追記：Mac内蔵画像生成で8原画を制作済み。以下は受け渡し時点の記録です。現在の成果物と検証は README.md、verification.md を参照してください。

製薬企業向けページの未完了作業を、Macの内蔵画像生成機能で完了してください。設計の提案だけで終了せず、8枚の新規原画を制作し、6言語ページへ組み込み、検証して本番反映してください。ユーザーは本番マージまで許可済みです。

## 作業開始

- Repository: https://github.com/SpecialistDoctors-Inc/simy-home
- Branch: `codex/pharma-manga-scenes`
- Draft PR: https://github.com/SpecialistDoctors-Inc/simy-home/pull/147
- Production: https://simy.one/for/pharmaceutical-companies/
- Macに既存checkoutがあれば変更を確認して利用し、なければ専用ディレクトリへcloneしてください。既存の変更を上書きしないでください。
- まず画像生成スキルを読み、内蔵の画像生成ツールが利用できることを確認してください。前のNVIDIAホストでは提供されていませんでした。Macでも使えることは未確認です。
- Runway契約や追加課金を前提にしないでください。API fallbackは許可済みですが、前環境にAPIキーはありませんでした。

## 必読の既存仕様

- `docs/pharmaceutical-manga/storyboard.md`
- `docs/pharmaceutical-manga/art-prompts.json`
- `docs/pharmaceutical-manga/prompts/scene-01.txt` ～ `scene-08.txt`
- `docs/pharmaceutical-manga/README.md`

参照原画は `site/assets/engineer-manga/release-crew-ja.webp`。同じ顔立ちの登場人物を使用し、背景、カメラ位置、姿勢、表情、全身の動きを新しく描いてください。既存顔画像の切り抜きや説明文の追加だけでは未達です。

## 8場面

1. 実面談：医師の肩越しに、患者集団について問われ説明が止まるMR。
2. 面談後：録音を聞き、先生が確認したかった患者背景に気づく。
3. 前回の発言と承認済み資料から、その先生が聞きそうな問いが組み立てられる。
4. スマホのAI医師と練習。資料の説明を急ぎ、再びつまずく。
5. 同じ場所で資料を置き、患者背景を質問する。姿勢と表情も変える。
6. 同じ医師、同じ部屋の次の実面談。条件を確認でき、院内の役割分担が次の課題になる。
7. 新しい録音から練習内容に院内分担が加わる。更新前後を絵で示す。
8. MRと育成担当が具体的な課題と次の練習を確認する。

重点は1と6の変化、4と5の行動変化、7の練習内容の更新です。医師の顔と面談室の連続性を保ち、AI医師は端末内の練習と分かるようにしてください。台詞は画像に焼き込まず、既存の6言語HTMLで表示します。

## 納品と組み込み

- 8枚すべて新規制作。目視して人物の一貫性と構図の違いを検証。
- 最終WebP: `site/assets/pharmaceutical-companies/manga-v2/scene-01.webp` ～ `scene-08.webp`
- PNGマスターは配信対象外に保存。
- `scripts/pharmaceutical_manga_art.py` とCSSは準備済み。8枚が揃えば全言語へ挿入されます。
- 現在は新規原画0/8。既存の本番画像は旧版です。テストfixtureやdry-runを完成原画として扱わないでください。

```bash
python3 scripts/build-pharmaceutical-pages.py --require-manga-art
python3 scripts/build-pharmaceutical-pages.py --check --require-manga-art
python3 scripts/build-localized-home.py --check
python3 scripts/check-home-seo.py
python3 scripts/check-site-seo.py
node --test tests/*.test.cjs
git diff --check
```

6言語のデスクトップとモバイルをブラウザで確認し、PR #147を完成させてmainへマージ。GitHub ActionsのS3/CloudFrontデプロイ成功後、本番の画像と表示を確認してください。サイトはAWSで、Vercelではありません。

採用済みヒーローは「その先生を知る。／その先生に合わせて、練習する。」です。原画制作に合わせて無断で戻さないでください。

SIMYの以前の監視ループは完了済みです。新たな監視の明示依頼はないため、再起動しないでください。
