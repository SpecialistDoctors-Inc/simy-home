"""Build a concise Japanese PDF with explicitly labelled instructional diagrams."""
import argparse
import hashlib
import json
from pathlib import Path
from html import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.12'
GUIDE_DATE = '2026-11-08'
DISPLAY_DATE = GUIDE_DATE.replace('-', '.')
W, H = A4
M = 42
CW = W - 2*M
INK = colors.HexColor('#242339')
MUTED = colors.HexColor('#656578')
ACCENT = colors.HexColor('#6554BD')
PALE = colors.HexColor('#F3F1FA')
LINE = colors.HexColor('#E0DDEB')


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    fonts = ROOT / 'site/vendor/report-pdf'
    pdfmetrics.registerFont(TTFont('JP', str(fonts/'NotoSansJP-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('JPBold', str(fonts/'NotoSansJP-Bold.ttf')))
    pdfmetrics.registerFontFamily('JP', normal='JP', bold='JPBold', italic='JP', boldItalic='JPBold')
    target = output / 'HPローカル編集_はじめ方.pdf'
    c = canvas.Canvas(str(target), pagesize=A4, pageCompression=1)
    c.setTitle(f'HP ローカル編集の使い方 {VERSION}')
    c.setAuthor('AwakApp Inc.')

    def text(value, top, x=M, width=CW, size=11, color=INK, bold=False):
        p = Paragraph(value, ParagraphStyle('body', fontName='JPBold' if bold else 'JP',
            fontSize=size, leading=size*1.65, textColor=color, wordWrap='CJK'))
        _, h = p.wrap(width, H)
        assert top+h < H-35, (value[:40], top+h)
        p.drawOn(c, x, H-top-h)
        return top+h

    def box(top, height, x=M, width=CW, fill=PALE):
        c.setFillColor(fill); c.setStrokeColor(LINE)
        c.roundRect(x,H-top-height,width,height,10,fill=1,stroke=1)

    def button(label, top, x=M, width=140, primary=True):
        c.setFillColor(ACCENT if primary else colors.white);c.setStrokeColor(LINE)
        c.roundRect(x,H-top-34,width,34,8,fill=1,stroke=not primary)
        text(label,top+7,x+10,width-20,10,colors.white if primary else INK)

    def page(number, title, subtitle):
        c.setFillColor(ACCENT);c.rect(M,H-36,26,3,fill=1,stroke=0)
        text(title,49,size=22,bold=True)
        text(subtitle,89,size=10,color=MUTED)
        c.setStrokeColor(LINE);c.line(M,41,W-M,41)
        c.setFont('JP',8);c.setFillColor(MUTED)
        c.drawString(M,23,f'HP ローカル編集 {VERSION}  /  {DISPLAY_DATE}')
        c.drawRightString(W-M,23,f'{number} / 4')

    page(1,'プラグインを導入する','MacのApple Silicon（M1以降）用')
    y=text('Codexを使えるデスクトップアプリにログインし、運用担当から配布セットとHP用Googleアカウントの案内を受け取ります。',125)
    y=text('1　配布セットを解凍する',y+21,size=13,bold=True)
    y=text('中のプラグインZIPを、Codexの会話へ添付します。',y+6)
    y=text('2　Codexに導入を依頼する',y+18,size=13,bold=True)
    box(y+10,116)
    text('このHPプラグインを導入して、編集を始めたいです。<br/>導入済みなら、作業中の変更を引き継いで更新してください。',y+23,M+15,CW-30,10.5)
    y+=143
    y=text('3　プラグインを追加して接続する',y,size=13,bold=True)
    y=text('Codexが導入状態を確認します。本人の操作が必要なら「HP ローカル編集」を追加します。今回の版が読み込まれず再起動を案内された場合は、作業を保存して再起動します。その後、Google接続を完了してください。',y+6)
    y=text('4　接続後、同じ会話で続ける',y+18,size=13,bold=True)
    y=text('元の会話で「続けて」と送ります。Codexの返信で医院名とURLを確認し、編集画面を開きます。サイトが複数あるときは、Codexの質問に答えて選びます。',y+6)
    y=text('ChatGPT用とHP用Googleのアカウントは、メールアドレスが異なっていても使えます。パスワードや確認コードはログイン画面に入力します。',y+19,size=10,color=MUTED)
    text('詳しい依頼文と、ファイルを添付できない場合の手順は、同梱のMarkdown手順書にあります。',y+12,size=9.5,color=MUTED)
    c.showPage()

    page(2,'手元のページを直す','Google接続後、導入の続きを進めると編集画面が開きます')
    y=text('ブラウザーに確認ページが開きます。右下のマークを押して、チャットで修正を依頼してください。',125)
    text('操作イメージ（図解）',y+18,size=9,color=MUTED)
    top=y+42
    box(top,257,fill=colors.white)
    text('手元のホームページ',top+17,M+18,225,12,bold=True)
    text('修正が終わると<br/>ページの表示が更新されます。',top+60,M+18,200,11,color=MUTED)
    x=M+237; width=CW-253
    box(top+14,228,x,width,PALE)
    text('ホームページの編集',top+26,x+13,width-26,11,bold=True)
    text('診療時間の「18時まで」を<br/>「19時まで」に変えてください。',top+64,x+13,width-26,10.5)
    text('手元のページを変更しました。',top+122,x+13,width-26,10.5)
    text('確認用 v1　 公開中 v1',top+164,x+13,width-26,9,color=MUTED)
    button('確認用に反映',top+191,x+13,130)
    y=top+278
    y=text('続けて直したいとき',y,size=13,bold=True)
    y=text('「見出しを少し小さくして」「さっきの診療時間を元に戻して」など、普段の言葉で指示します。',y+6)
    y=text('Enterで送信　／　Shift + Enterで改行',y+18,size=11,bold=True)
    y=text('日本語の変換を確定するEnterでは送信しません。',y+5,size=10,color=MUTED)
    y=text('ブラウザー内のチャットは、このHPの編集用の会話です。別のCodexの会話で伝えた内容が必要なら、こちらにも伝えてください。',y+18,size=10)
    text('画像の追加などチャットで扱えない変更は、Codexアプリへファイルと依頼内容を渡します。',y+12,size=10,color=MUTED)
    c.showPage()

    page(3,'確認して公開する','手元 → 確認用サイト → 公開中のホームページ')
    y=text('手元の内容がよければ「確認用に反映」を押します。反映が終わったら「確認用サイトを開く」で文章・リンク・画像・スマートフォン表示を確認します。',125)
    box(y+16,48)
    text('確認用 v2　／　公開中 v1',y+27,M+16,CW-32,12,bold=True)
    y+=82
    y=text('確認用サイトがよければ「公開する」を押し、変更概要を確認します。確認画面の「公開する」で確定します。',y)
    text('公開前の操作イメージ（図解）',y+14,size=9,color=MUTED)
    top=y+37
    box(top,246,fill=colors.white)
    text('サンプルクリニック',top+14,M+18,CW-36,9,color=MUTED)
    text('公開内容を確認',top+34,M+18,CW-36,16,bold=True)
    text('公開中 v1 → 公開後 v2',top+66,M+18,CW-36,10,color=MUTED)
    text('診療時間',top+100,M+18,CW-36,11,bold=True)
    text('変更前　18時まで<br/>変更後　19時まで',top+123,M+18,CW-36,11)
    text('変更後を見る　　公開中を見る',top+172,M+18,CW-36,10,color=ACCENT)
    button('公開する',top+201,M+18,112)
    button('閉じる',top+201,M+140,78,False)
    y=top+268
    y=text('「公開済みの内容」と表示されたら、「公開サイトを開く」で結果を確認します。処理状況は自動で更新されます。',y)
    y=text('確認用 v2 / 公開中 v2 は同じ版です。番号は確認用への反映完了時に付き、公開すると同じ番号を引き継ぎます。反映日時は表示にカーソルを重ねると見られます。',y+14,size=10,color=MUTED)
    text('変更が多い場合は概要と残り件数を表示します。確認用サイトの実際の表示も確認してください。',y+10,size=9.5,color=MUTED)
    c.showPage()

    page(4,'次回の編集と困ったとき','前の作業を引き継いで再開できます')
    box(125,84)
    text('次回はCodexにこう伝えます',137,M+15,CW-30,10,color=ACCENT)
    text('前回のHP編集を再開し、確認画面を開いてください。',163,M+15,CW-30,12)
    y=226
    for heading,body in [
        ('修正が途中で止まった','「修正を再開」「中断した変更を再開」が表示されたら、そのボタンを使います。解消しなければCodexに続きの確認を依頼します。'),
        ('反映や公開の結果を確認中','自動確認を待ちます。長く続く場合は「前回の処理がどこまで完了したか確認して」とCodexへ伝えます。'),
        ('処理状況のボタン','「同じ依頼で再確認」は受付結果を確認します。「処理を再開」は停止した処理を再開します。「公開結果を見る」は前回の変更概要と公開結果を開きます。'),
        ('確認期限が切れた','確認画面を閉じ、チャット下の「公開する」から開き直します。'),
        ('ログイン・接続で止まる','登録したGoogleアカウントを確認し、画面の案内に従って再接続します。'),
        ('更新ZIPを受け取った','CodexへZIPを渡し、作業を引き継いで更新するよう依頼します。案内に従って保存・再起動し、新しい会話でHPプラグインを選びます。'),
        ('Macが起動を止める・警告が出る','表示内容を運用担当に伝え、配布物と実行環境を確認してもらいます。'),
    ]:
        y=text(heading,y,size=12,bold=True)
        y=text(body,y+3,size=10)+12
    y=text('この資料の図について',y+4,size=10,bold=True)
    y=text(f'操作イメージは{VERSION}の表記に合わせた図解です。最新の実画面撮影は、ブラウザー操作機能が無効のため未実施です。',y+4,size=9,color=MUTED)
    text('<link href="https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually" color="#6554BD">公式のローカルプラグイン導入方法</link>',y+10,size=9)
    c.save()
    receipt = {'version': VERSION, 'date': GUIDE_DATE,
        'pdf_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'customer_guide_sha256': hashlib.sha256((ROOT/'docs/hp-single-plugin-customer-guide.md').read_bytes()).hexdigest()}
    (output/'guide-build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return target


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output/hp-plugin-0.3.12-20261108')
    args=parser.parse_args()
    print(build(args.output))
