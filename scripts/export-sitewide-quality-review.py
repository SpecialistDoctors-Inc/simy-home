#!/usr/bin/env python3
"""Export the evidence-backed review to Excel. Requires openpyxl in a dev venv."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.properties import CalcProperties

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
DOCS = ROOT / 'docs/sitewide-quality'
LONG_TEXT = []

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags=[];self.title='';self.in_title=False;self.feed(source)
    def handle_starttag(self,t,a):
        self.tags.append((t,dict(a)))
        if t=='title':self.in_title=True
    def handle_endtag(self,t):
        if t=='title':self.in_title=False
    def handle_data(self,s):
        if self.in_title:self.title+=s

def read_json(p, fallback=None):
    return json.loads(p.read_text()) if p.exists() else fallback

def plain(s):
    return re.sub(r'\*\*|`','',re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)).strip()

def redact(s):
    # Only remove high-confidence credential values; preserve requirement text.
    s=re.sub(r'(?i)(password|api[_-]?key|access[_-]?token|secret|パスワード)(\s*[:=：]\s*)([^\s,;"\']+)',r'\1\2[機密値省略]',s)
    s=re.sub(r'''(?i)((?:password|api[_-]?key|access[_-]?token|secret|パスワード)["']?\s*[:=：]\s*["']?)([^\s,"']+)''',r'\1[機密値省略]',s)
    s=re.sub(r'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+','[機密値省略]',s)
    return re.sub(r'\b(?:sk_live_|sk_test_|ghp_|github_pat_)[A-Za-z0-9_\-]{12,}', '[機密値省略]',s)

def request_part(s):
    if s.lstrip().startswith(('# AGENTS.md instructions', '<environment_context>', '<permissions instructions>', '<recommended_plugins>', 'Side conversation boundary.', '<hook_prompt', 'Message from SIMY,', '<external_codex_apps_open_page>', '<external_codex_apps_selected_page')):return ''
    if '## My request:' in s:return s.split('## My request:',1)[1].strip()
    s=re.sub(r'<(?:external_codex_apps_[^>]*|in-app-browser-context)\b[^>]*>[\s\S]*?</(?:external_codex_apps_[^>]*|in-app-browser-context)>','',s)
    return s.strip()

def topic(title,body):
    text=title+' '+body
    pairs=[(r'ロセンズ|路線価|rosenz','路線価・ロセンズ'),(r'製薬|医師別|pharma','製薬企業'),
           (r'弁護士|法律事務所|law.firm','法律事務所'),(r'Financial Planner|ファイナンシャル|ソニー生命|FP','FP'),
           (r'HP診断|クリニック|医院|HP管理|休診','HP管理・クリニック'),(r'CLI|Engineer|エンジニア','エンジニア・CLI'),
           (r'SEO|共起語|GSC|インデックス','SEO・検索公開'),(r'header|ヘッダー|signup|料金|headline','共通導線・コピー・料金')]
    return ' / '.join(label for rx,label in pairs if re.search(rx,text,re.I)) or '関連資料・共通要件'

def history_sheets(wb,history):
    records=history['records'];threads=[];messages=[];candidates=[];corrections=[];sequence=0
    for record in records:
        meta=record['metadata'];title=meta['title'];msgs=record['messages']
        source_kind=meta.get('sourceKind') or ('派生・引継ぎスレッド（初期プロンプトの著者は未確定）' if re.search(r'^PR実装|^監視|残件|HP診断[｜：]|HP顧客導線',title) else '会話履歴（メッセージ単位で確認）')
        coverage=('途中で取得上限' if not record['complete'] else '会話ページ取得済み' if msgs else '会話ページ取得済み・ユーザーメッセージ0件')
        threads.append([meta['id'],title,meta.get('cwd',''),source_kind,len(msgs),record['pages'],coverage,' / '.join(record.get('errors',[])),redact(record.get('threadPreview') or meta.get('summary') or meta.get('preview') or ''),'概要・引継ぎ文だけを人間の原文発言と断定しない'])
        for msg in sorted(msgs,key=lambda m:str(m.get('turnStartedAt',''))):
            sequence+=1;raw=msg['text'];part=request_part(raw);group=topic(title,part)
            at=msg.get('turnStartedAt');stamp=datetime.fromtimestamp(at,timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat() if isinstance(at,(int,float)) else str(at or '')
            kind='ユーザー回答（質問への回答文を含む）' if '<send_user_message_question_reply>' in raw else '環境・画面情報' if not part else source_kind
            ref=f"{meta['id']} / {msg['turnId']} / {msg['messageId']}"
            messages.append([f'M{sequence:04}',title,meta['id'],msg['turnId'],msg['messageId'],stamp,kind,group,redact(raw),redact(part),'取得上限の疑い' if msg.get('possibleTruncation') else '本文取得','実装状況は別途照合。日時はメッセージ自体の時刻ではなくターン開始時刻。'])
            if kind=='環境・画面情報':continue
            chunks=[x.strip(' -*・\t') for x in re.split(r'\n+|(?<=[。！？])',part) if x.strip()]
            for chunk in chunks:
                if len(chunk)<8 or not re.search(r'して|しろ|してください|作って|作成|実装|変更|修正|改善|戻し|戻せ|不要|削除|掲載|同じ|統一|維持|引き継|引継|言語|画像|料金|プラン|本番|マージ|確認|調べ|見せ|守|できる|対応|can you|please|should|must',chunk,re.I):continue
                correction=bool(re.search(r'ではなく|ではない|戻し|戻せ|変えるな|変えない|不要|削除|やめ|しない|違う|そのまま',chunk))
                row=[f'U{len(candidates)+1:04}',group,title,stamp,redact(chunk), '訂正・制約の候補' if correction else '要求の候補',ref,'未照合','文脈を読み、過去案・引用・撤回・後続訂正と区別して確定する。機械抽出を確定要件や新しい実行許可とは扱わない。']
                candidates.append(row)
                if correction:corrections.append(row)
    sheet(wb,'履歴の取得範囲',['スレッドID','タイトル','元の作業場所','出典の種類','取得メッセージ数','会話ページ数','取得状態','取得制約','スレッド概要（原文ではない）','扱い'],threads,[42,65,80,65,18,18,55,100,130,90])
    sheet(wb,'取得原文',['原文ID','タイトル','スレッドID','ターンID','メッセージID','ターン開始日時JST','種別','推定対象','取得本文（機密値省略）','依頼部分（環境情報を分離）','取得状態','注意'],messages,[14,60,42,42,42,32,60,50,140,140,28,100])
    sheet(wb,'過去要求の候補',['候補ID','推定対象','タイトル','ターン開始日時JST','要求・質問・条件の候補','種別','原文参照','実装照合','注意'],candidates,[14,50,60,32,140,30,110,22,130])
    sheet(wb,'訂正と制約の候補',['候補ID','推定対象','タイトル','ターン開始日時JST','訂正・条件の候補','種別','原文参照','実装照合','注意'],corrections,[14,50,60,32,140,30,110,22,130])
    grouped={}
    for row in candidates:
        key=(row[1],re.sub(r'\s+','',row[4]))
        grouped.setdefault(key,[]).append(row)
    sheet(wb,'同文要求の集約',['推定対象','要求候補の本文','出現回数','最初のターン日時JST','最後のターン日時JST','原文参照一覧','集約の限界'],[[rs[0][1],rs[0][4],len(rs),min(r[3] for r in rs),max(r[3] for r in rs),'\n'.join(r[6] for r in rs),'空白を除く同文を集約。同義文・撤回・最新の優先関係は未裁定。'] for rs in grouped.values()],[50,140,18,35,35,140,100])
    # The row count is not fixed: a subsequent recovery may add source messages.
    wb['取得原文'].title='取得原文'+str(len(messages))+'件'
    for entry in LONG_TEXT:
        if entry[1]=='取得原文':entry[1]=wb['取得原文'+str(len(messages))+'件'].title
    return {'threads':len(threads),'messages':len(messages),'requirementCandidates':len(candidates),'correctionCandidates':len(corrections),'groupedRequirements':len(grouped)}

def sheet(wb,name,headers,rows,widths=None):
    ws=wb.create_sheet(name);ws.append(headers)
    for row in rows:
        values=[]
        for col,value in enumerate(row,1):
            if isinstance(value,str) and len(value)>30000:
                reference=f'LT{len(LONG_TEXT)+1:05}'
                chunks=[value[i:i+28000] for i in range(0,len(value),28000)]
                for part,chunk in enumerate(chunks,1):
                    LONG_TEXT.append([reference,name,ws.max_row+1,col,part,len(chunks),chunk])
                value=f'全文は「長文セルの全文」{reference}（{len(chunks)}分割）を参照。\n'+value[:1500]
            values.append("'"+value if isinstance(value,str) and value.startswith(('=','+','-','@')) else value)
        ws.append(values)
    ws.freeze_panes='C2' if len(headers)>5 else 'A2'
    ws.sheet_view.showGridLines=False
    ws.auto_filter.ref=ws.dimensions
    for cell in ws[1]:
        cell.fill=PatternFill('solid',fgColor='17365D');cell.font=Font(name='Yu Gothic',bold=True,color='FFFFFF');cell.alignment=Alignment(wrap_text=True,vertical='center')
    ws.row_dimensions[1].height=34
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font=Font(name='Yu Gothic',size=10)
            cell.alignment=Alignment(vertical='top',wrap_text=True)
            if isinstance(cell.value,str) and cell.value.startswith(('https://','http://')) and '\n' not in cell.value:
                cell.hyperlink=cell.value;cell.font=Font(name='Yu Gothic',size=10,color='0563C1',underline='single')
            if cell.value in ['完了','合格']:
                cell.fill=PatternFill('solid',fgColor='E2F0D9')
            elif cell.value in ['資料待ち','外部確認待ち','未確認','要実測','未着手','検証中','部分完了']:
                cell.fill=PatternFill('solid',fgColor='FFF2CC')
            elif cell.value=='不合格':
                cell.fill=PatternFill('solid',fgColor='FCE4D6')
        ws.row_dimensions[row[0].row].height=min(120,max(30,max(len(str(c.value or '')) for c in row)//30*13+18))
    for i,h in enumerate(headers,1):
        ws.column_dimensions[ws.cell(1,i).column_letter].width=(widths[i-1] if widths and i<=len(widths) else 28)
    if rows:
        table=Table(displayName='ReviewTable'+str(len(wb.worksheets)),ref=ws.dimensions)
        table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True)
        ws.add_table(table)
    ws.print_options.horizontalCentered=True
    ws.sheet_properties.pageSetUpPr.fitToPage=True
    ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A3;ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
    ws.print_title_rows='1:1'
    return ws

def extract_experts():
    result=[]
    specs=[('seo-review.md',[('10の分析視点','SEO')]),('design-ux-review.md',[('デザイン分野の10視点','デザイン'),('UX分野の10視点','UX')]),('accessibility-architecture-review.md',[('アクセシビリティ：10視点','アクセシビリティ'),('性能とアーキテクチャ：10視点','性能・アーキテクチャ')])]
    for file,sections in specs:
        source=(DOCS/file).read_text()
        for heading,domain in sections:
            block=source.split(heading,1)[1].split('\n##',1)[0]
            count=0
            for line in block.splitlines():
                if not line.startswith('|'):continue
                cells=[c.strip() for c in line.strip('|').split('|')]
                if len(cells)!=3 or not re.search(r'https?://',cells[1]):continue
                count+=1;url=re.search(r'https?://[^\s)]+',cells[1])[0]
                result.append([f'E{len(result)+1:02}',domain,plain(cells[0]),url,plain(cells[1]),plain(cells[2]),'公開活動からの当方の適用仮説。本人の今回の発言・参加・推薦ではない。','本文取得／HTTP確認の詳細は元レビュー参照。HTTP200だけで精読を意味しない。','docs/sitewide-quality/'+file])
            assert count==10,(file,heading,count)
    assert len(result)==50
    return result

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--output',type=Path,default=DOCS/'SIMY_全ページレビューと改善計画_20261119.xlsx');cli.add_argument('--history',type=Path,help='Private, external history JSON. Output must be outside the public repository.');cli.add_argument('--search-console',type=Path,help='Private authenticated Search Console observations; output must be outside repository.');cli.add_argument('--ai-review',type=Path,help='Private actual AI responses and conversation URLs; export outside repository.');cli.add_argument('--gsc-export',type=Path,help='Private official Search Console Excel; export outside repository.');args=cli.parse_args()
    if (args.history or args.search_console or args.ai_review or args.gsc_export) and args.output.resolve().is_relative_to(ROOT):
        raise SystemExit('Export private history outside the public repository with --output.')
    inventory=read_json(ROOT/'docs/seo/sitewide-page-inventory.json')
    generated_content={url.lstrip('/')+('index.html' if url.endswith('/') else ''): 'scripts/content-pages.json → scripts/build-content-pages.py'
                       for p in read_json(ROOT/'scripts/content-pages.json')['pages'] for url in p['paths'].values()}
    plan=read_json(DOCS/'improvement-plan.json');findings=plan['findings']
    browser=read_json(DOCS/'evidence/browser-expanded.json',{});browser_rows=browser.get('results',[])
    live=read_json(DOCS/'evidence/production-http.json',{}).get('results',[])
    by_file={}
    for r in browser_rows:by_file.setdefault(r['file'],[]).append(r)
    live_map={r['file']:r for r in live}
    wb=Workbook();wb.remove(wb.active);wb.calculation=CalcProperties(calcId=191029,fullCalcOnLoad=True)
    wb.properties.title='SIMY 全ページレビューと改善計画';wb.properties.creator='Codex';wb.properties.subject='確認済み事実・適用仮説・未確認を分離した改善管理'
    intro=[
        ['対象','https://simy.one/ の公開静的サイト。実装元simy-home。199 HTML／index159／nonindex40。'],
        ['更新日',plan['date']+' 日本時間（元レビュー作成2026-11-19）'],
        ['このExcelの用途','指摘・根拠・採否・改善手順・対象ページ・実施状況・検証を追跡する。フィルターで分野／優先度／状態を絞り込める。'],
        ['専門家50名の意味','客観的な世界ランキングや本人参加の討論ではない。公開資料を参考に当方が行った仮想レビュー。資料取得の制約を保持。'],
        ['完了の意味','各行で定義したローカル作業と検証の完了。本番反映・過去全要求の充足とは別。'],
        ['全体の受入','R1〜R8の必須条件。平均点・件数ベース進捗で未達を相殺しない。'],
        ['過去依頼の原文','未取得の関連履歴がある。全Codexスレッドを網羅済みとは扱わない。'],
        ['公開状況',next(r for r in findings if r['id']=='Q35')['status']+'：'+next(r for r in findings if r['id']=='Q35').get('verificationResult','実行計画Q35を参照。')],
        ['検査の範囲','静的全件／ブラウザー実施条件／外部計測を分離。外部リクエストを遮断したローカルChromiumでの検査は本番の実利用性能ではない。'],
        ['優先順位','P1=到達性・事実性・要件/公開の阻害、P2=品質改善/リスク低減、P3=成果仮説・継続改善。'],
        ['工数','実行計画の工数は計画時の概算。実績時間、納期、担当者の約束ではない。'],
        ['更新方法','improvement-plan.jsonと検証JSONを更新しscripts/export-sitewide-quality-review.pyを再実行。Excel内だけの編集は再生成時に上書きされる。']]
    sheet(wb,'はじめに',['項目','説明'],intro,[26,125])
    counts=Counter(r['status'] for r in findings)
    summary=[['指摘・管理項目',len(findings),'不具合だけでなく候補・既存合格・外部確認も含む'],['HTMLファイル',len(inventory),'正規URL数とは異なる'],['index',sum(v['policy']=='index' for v in inventory.values()),'公開方針を維持'],['専門家視点',50,'各分野10、本人参加なし'],['ブラウザーケース',len(browser_rows),'実施した条件のみ'],['ブラウザー指摘ケース',len(browser.get('summary',{}).get('failed',[])),'ケース数であり固有不具合件数ではない']]
    summary += [[status,counts[status],'定義ははじめに・状態辞書を参照'] for status in plan['statusLegend']]
    ws=sheet(wb,'概要',['指標','件数','注記'],summary,[35,18,95])
    ws['E1']='状態変更に連動するExcel式';ws['E2']='完了行数';ws['F2']=f'=COUNTIF(指摘一覧!F2:F{len(findings)+1},"完了")';ws['E3']='未完了行数';ws['F3']=f'=COUNTA(指摘一覧!A2:A{len(findings)+1})-F2'
    ws.column_dimensions['E'].width=32;ws.column_dimensions['F'].width=18
    chart=BarChart();chart.title='状態別の項目数（生成時点）';chart.add_data(Reference(ws,min_col=2,min_row=8,max_row=7+len(plan['statusLegend'])),titles_from_data=False);chart.set_categories(Reference(ws,min_col=1,min_row=8,max_row=7+len(plan['statusLegend'])));ws.add_chart(chart,'E6')
    ws=sheet(wb,'指摘一覧',['ID','分野','優先度','区分','指摘・管理項目','状態','対象範囲','変更前の観察・懸念','影響と修正の必要性','改善内容','合格条件','根拠・実装参照','検証結果','関連基準','依存条件','次の行動'],[[r['id'],r['domain'],r['priority'],r['kind'],r['title'],r['status'],r['scope'],r['before'],'関連基準'+r['criterion']+'の達成・確認に必要。候補と実測不具合を区分列で区別。',r['improvement'],r['acceptance'],r['evidence'],r.get('verificationResult','未記録'),r['criterion'],r['dependency'],r['nextAction']] for r in findings],[10,22,10,20,40,19,40,65,42,70,65,65,80,15,42,55])
    dv=DataValidation(type='list',formula1='"完了,検証中,部分完了,未着手,資料待ち,外部確認待ち"');ws.add_data_validation(dv);dv.add(f'F2:F{len(findings)+1}')
    sheet(wb,'実行計画',['順序','ID','優先度','実施する作業','対象','状態','依存・開始条件','実装担当','検証方法・完了条件','概算工数','次の行動','公開との関係'],[[i,r['id'],r['priority'],r['improvement'],r['scope'],r['status'],r['dependency'] or '依存なし／確認済み事実に基づき実行可能',r['owner'],r['acceptance'],r['estimatedEffort'],r['nextAction'],'ローカル完了と本番反映は別。Q35で管理'] for i,r in enumerate(findings,1)],[9,10,10,75,42,19,45,30,70,25,60,40])
    page_rows=[];checks=[]
    for name,item in sorted(inventory.items()):
        source=(SITE/name).read_text();p=Page(source)
        attrs=lambda t:[a for tag,a in p.tags if tag==t]
        meta={a.get('name',a.get('property')):a.get('content','') for a in attrs('meta')}
        canonical=next((a.get('href') for a in attrs('link') if a.get('rel')=='canonical'),'')
        main=[a for t,a in p.tags if t=='main' or a.get('role')=='main']
        skips=[a for t,a in p.tags if t=='a' and 'skip' in a.get('class','')]
        rendered=bool(attrs('body')) and not re.search(r'http-equiv=["\']refresh',source,re.I) and name not in ['auth-callback.html'] and not name.startswith('google-site-verification-')
        imgs=attrs('img');missing_alt=sum('alt' not in a for a in imgs);missing_size=sum(not (a.get('width') and a.get('height')) for a in imgs)
        cases=by_file.get(name,[]);issues=[r for r in cases if r['mainCount']!=1 or not r['skipVisible'] or not r['mainFocused'] or r['overflow']>1 or r['contentLength']==0]
        generator=generated_content.get(name,'site/'+name+'（静的原稿）')
        if name in ['index.html','ja.html','es.html','fr.html','hi.html','zh-Hans.html']:
            generator='scripts/home-ja-manga.html・home-locales.js → build-localized-home.py'
        elif name.startswith('for/') and 'financial-planners/' in name:
            generator='scripts/financial-planner-locales.json → build-financial-planner-pages.py'
        elif name.startswith('for/') and 'pharmaceutical-companies/' in name:
            generator='scripts/pharmaceutical-ja.html・pharmaceutical-locales.json → build-pharmaceutical-pages.py'
        elif name.startswith('for/') and 'engineers/' in name:
            generator='scripts/engineering-cli-*.html・engineering-copy.json → build-engineering-pages.py'
        page_rows.append([name,canonical,p.title,item.get('language',''),item['policy'],'描画文書' if rendered else '転送・認証・検証等',len(main),len(skips),len(imgs),missing_alt,missing_size,len(cases),len(issues),'未確認','docs/seo/sitewide-page-inventory.json',generator,'scripts/site_header.py → page_accessibility.py（通常描画文書）'])
        def add_check(code,criterion,result,observed,method,next_step=''):
            checks.append([name,canonical,item['policy'],code,criterion,result,observed,method,'site/'+name,next_step])
        add_check('C01','過去の全依頼の充足','未確認','原文取得・照合が未完了','原文とページ別要件の照合','関連スレッド原文を取得')
        add_check('C02','公開方針の明示','合格',item['policy'],'全HTML台帳と照合')
        add_check('C03','index/robots整合','合格' if (('noindex' not in meta.get('robots','')) if item['policy']=='index' else 'noindex' in meta.get('robots','')) else '不合格',meta.get('robots',''),'静的HTML')
        add_check('C04','canonicalの存在','合格' if canonical else ('対象外' if item['policy']!='index' else '不合格'),canonical,'静的HTML。正規性全体は既存SEO checkerで確認')
        add_check('C05','本文ランドマーク','対象外' if not rendered else '合格' if len(main)==1 else '不合格',f'main={len(main)}','HTMLParser')
        matched=bool(main and any(a.get('href')=='#'+main[0].get('id','') for a in skips))
        add_check('C06','本文へのskipターゲット','対象外' if not rendered else '合格' if matched else '不合格',str([a.get('href') for a in skips]),'静的ターゲット照合。操作結果はC10')
        add_check('C07','画像alt属性','合格' if missing_alt==0 else '不合格',f'画像{len(imgs)}／alt欠落{missing_alt}','装飾alt空文字を許可。意味の適切さは別レビュー')
        add_check('C08','画像領域予約','要実測' if missing_size else '合格',f'width/height欠落{missing_size}','属性欠落だけではCSS aspect-ratio等を含むCLS不具合と断定しない','CSSと実表示を確認' if missing_size else '')
        add_check('C09','viewport','合格' if meta.get('viewport') else '対象外' if not rendered else '不合格',meta.get('viewport',''),'静的HTML')
        add_check('C10','実ブラウザーのmain/skip/横幅','対象外' if not rendered else '未確認' if not cases else '合格' if not issues else '不合格',f'実施{len(cases)}／指摘{len(issues)}','Chromium・1browser・reduce・外部通信遮断。幅はブラウザー検査sheet','固有の失敗条件を確認' if issues else '')
        add_check('C11','本文の事実・提供条件','未確認','静的構造検査だけでは証明しない','製品仕様・原文・出典との意味照合','対象別に確認')
        l=live_map.get(name)
        add_check('C12','現行本番HTTP','対象外' if item['policy']!='index' else '未確認' if not l else '合格' if l.get('status')==200 else '不合格',str(l or ''),'現行本番への読み取り。変更版公開の証明ではない')
    sheet(wb,'全199ページ',['ファイル','canonical','ページタイトル','言語','公開方針','用途','main数','skip数','画像数','alt欠落','寸法属性欠落','browserケース','browser指摘','過去要件充足','台帳根拠','原稿・主生成器','共有生成処理'],page_rows,[48,62,70,12,18,25,10,10,10,10,13,14,14,20,60,85,70])
    sheet(wb,'ページ別検査',['ファイル','URL','公開方針','検査ID','品質条件','結果','観測値','方法・限界','根拠HTML','次の行動'],checks,[45,60,16,12,40,16,80,85,50,60])
    sheet(wb,'専門家50視点',['ID','分野','実践者','参考URL','公開資料名','今回への適用仮説','発言・参加の扱い','資料取得の制約','出典レビュー'],extract_experts(),[10,27,28,80,45,95,70,70,65])
    debates=[]
    for file in ['seo-review.md','design-ux-review.md','accessibility-architecture-review.md']:
        heading='';table_head=None
        for line in (DOCS/file).read_text().splitlines():
            if line.startswith('#'):heading=plain(line.lstrip('#'));table_head=None
            if not line.startswith('|'):continue
            cells=[plain(c.strip()) for c in line.strip('|').split('|')]
            if all(re.fullmatch(r'[- :]+',c or '-') for c in cells):continue
            if table_head is None:table_head=cells;continue
            if any('http' in c for c in cells):continue
            if 'ラウンド' in heading or '対立' in heading or '調整' in heading or '採否' in heading:
                debates.append([file,heading,cells[0],'\n'.join(f'{k}: {v}' for k,v in zip(table_head[1:],cells[1:])),'当方の設計上の比較。本人同士の実討論ではない。'])
    sheet(wb,'論点と採否',['元資料','ラウンド・分野','論点','反論・裁定・受入条件','方法'],debates,[55,50,50,140,65])
    quality=[]
    for line in (DOCS/'quality-standard.md').read_text().splitlines():
        if re.match(r'\| R[1-8] \|',line):quality.append([plain(c.strip()) for c in line.strip('|').split('|')]+['必須。未確認や未達を平均点で相殺しない'])
    sheet(wb,'品質基準',['ID','最低ライン','受入方法','合否方針'],quality,[10,90,110,60])
    reconciled=read_json(DOCS/'user-requirements-reconciliation.json',{}).get('requirements',[])
    if reconciled:
        sheet(wb,'過去依頼との照合',['ID','過去依頼の要点','対象','照合状態','確認内容・残る範囲','改善計画ID','スレッド名','原文スレッドID','原文ターンID','原文メッセージID'],[[r['id'],r['requirement'],r['scope'],r['status'],r['observed'],r['plan'],r['sourceTitle'],r['sourceThread'],r['sourceTurn'],r['sourceMessage']] for r in reconciled],[12,110,45,30,120,35,65,42,42,42])
    sheet(wb,'ブラウザー検査',['ファイル','幅CSS px','main数','先頭Tabのhref','skip表示','Enter後main focus','横はみ出しpx','本文文字数','判定','測定条件'],[[r['file'],r['width'],r['mainCount'],r.get('href'),r['skipVisible'],r['mainFocused'],r['overflow'],r['contentLength'],'合格' if r['mainCount']==1 and r['skipVisible'] and r['mainFocused'] and r['overflow']<=1 and r['contentLength']>0 else '不合格','local Chromium / reduced motion / 外部リクエスト遮断'] for r in browser_rows],[50,14,12,55,16,24,20,18,15,75])
    schema=read_json(DOCS/'evidence/schema-inventory.json',{}).get('results',[])
    if schema:
        sheet(wb,'構造化データ監査',['ファイル','schema型','項目','値・FAQテキスト','観測結果','方法・限界'],[[r['file'],r['type'],r['field'],json.dumps(r.get('value'),ensure_ascii=False) if 'value' in r else r.get('text',''),('可視本文に存在' if r['visibleTextContains'] else '可視本文に見つからず') if 'visibleTextContains' in r else '設定あり' if r['present'] else '未設定','静的存在・FAQ文字列の本文内存在のみ。質問と回答の対応や事実性を保証しない。ニュース更新日未設定をGoogle一律必須違反とはしない。'] for r in schema],[50,20,24,120,26,95])
    pairs=read_json(DOCS/'evidence/schema-inventory.json',{}).get('faqPairs',[])
    if pairs:
        sheet(wb,'FAQの対応1114件',['ファイル','質問','schemaの回答','可視FAQとの対応','方法・限界'],[[r['file'],r['question'],r['answer'],'合格' if r['matchingVisiblePair'] else '不合格','同じdetailsのsummaryに質問が一致し、その回答領域にschema回答が存在。回答内容の事実性・最新性は別途確認。'] for r in pairs],[50,80,150,22,110])
    evidence=[['前ターンの検証','verification.md','1648 testsと代表18ケース。今回追加分の結果はexecution-verification.mdを参照'],['今回のブラウザー','evidence/browser-expanded.json',f'{len(browser_rows)}ケース。未測定条件を測定済みにしない'],['今回のHTTP','evidence/production-http.json',f'{len(live)} URLs。現行本番に対する読み取りのみ'],['原文履歴の取得と照合','requirements-coverage.md','保存履歴4,185件を走査し206スレッド/1,870メッセージを統合。全候補の確定と本文照合は未完了。削除済み履歴は保証しない'],['専門家の根拠','各review.md','公開原則に基づく仮説。到達性確認と本文精読を区別'],['Excel生成','scripts/export-sitewide-quality-review.py','状態・観測値はJSON/HTMLから生成。ダッシュボード数値は生成時点スナップショット']]
    sheet(wb,'検証証跡と制約',['対象','証跡・参照','内容と限界'],evidence,[35,70,120])
    if (DOCS/'execution-verification.md').exists():
        sheet(wb,'今回の実行記録',['行','検証記録'],[[i,line] for i,line in enumerate((DOCS/'execution-verification.md').read_text().splitlines(),1) if line.strip()],[10,150])
    release=read_json(DOCS/'evidence/production-release.json',{})
    if release:
        sheet(wb,'本番配信の照合',['ファイル','確認URL','HTTP','配信SHA256','期待SHA256','一致','確認日時UTC','本番コミット','配信ジョブ','範囲・制約'],[[r['file'],r['url'],r.get('status',''),r.get('actualSha256',''),r.get('expectedSha256',''),'合格' if r['matches'] else '不合格',release['observedAt'],release['commit'],release['deploymentRun'],release['scope']] for r in release['results']],[55,85,12,72,72,15,35,50,90,110])
    progress=read_json(DOCS/'remaining-seven-progress.json',{})
    if progress:
        sheet(wb,'残る7項目の追加実行',['ID','項目','状態','今回の実装・検証','必要な人・データ・環境','次の行動'],[[r['id'],r['title'],r['status'],r['verificationResult'],r['dependency'],r['nextAction']] for r in progress['findings']],[12,50,25,150,100,120])
    sources=read_json(DOCS/'evidence/official-source-fetch.json',{}).get('results',[])
    if sources:
        sheet(wb,'公式資料の取得',['URL','参照ページ','HTTP','最終URL','bytes','取得と意味検証の区別'],[[r['url'],', '.join(sorted(set(r['pages']))),r.get('status',r.get('error','')),r.get('finalURL',''),r.get('bytes',0),r['assessment']] for r in sources],[100,55,30,100,18,110])
    locale_checks=read_json(DOCS/'evidence/axe-home-locales.json',{}).get('results',[])
    if locale_checks:
        sheet(wb,'追加ホーム検査',['ファイル','幅','横はみ出しpx','違反数','違反内容','読み上げ名','画像選択','検査範囲'],[[r['file'],r['width'],r['overflow'],len(r['violations']),json.dumps(r['violations'],ensure_ascii=False),r['languageName'],json.dumps(r['images'],ensure_ascii=False),'axe color-contrast/label-content-name-mismatchのみ。全WCAG適合や実読者評価の代替ではない。'] for r in locale_checks],[45,15,20,15,100,70,140,110])
    semantic=read_json(DOCS/'evidence/requirements-semantic-followup.json',{}).get('results',[])
    if semantic:
        sheet(wb,'原文と現行本文の追加照合',['依頼ID','ファイル','現行本文','照合根拠','裁定と限界'],[[r['requirement'],r['file'],r['observed'],r['evidence'],r['decision']] for r in semantic],[22,70,140,100,140])
    trial=read_json(DOCS/'evidence/download-trial-browser.json',{})
    if trial:
        sheet(wb,'無料体験の内容修正',['ファイル','言語','幅CSS px','質問','修正後の可視回答','FAQ schema回答','表示とschema一致','横はみ出しpx','申込URL','取得日時UTC','範囲・制約'],[[r['file'],r['language'],r['width'],r['question'],r['answer'],r['schemaAnswer'],'合格' if r['answer']==r['schemaAnswer'] else '不合格',r['overflow'],r['accountURL'],trial['observedAt'],trial['method']] for r in trial['results']],[55,20,18,65,150,150,25,25,120,35,100])
    visual=read_json(DOCS/'evidence/visual-followup.json',{})
    if visual:
        sheet(wb,'既存原画の追加目視',['ファイル','SHA256','確認内容','範囲・制約','方法'],[[r['file'],r['sha256'],r['assessment'],r['limitation'],visual['method']] for r in visual['results']],[95,75,150,140,110])
    signup=read_json(DOCS/'evidence/signup-browser.json',{}).get('results',[])
    fixed_signup=read_json(DOCS/'evidence/signup-local-browser.json',{}).get('results',[])
    if signup:
        by_locale={r['locale']:r for r in fixed_signup}
        sheet(wb,'申込言語の追加検査',['指定言語','本番HTTP','本番の表示言語','本番の観察','修正版の表示言語','修正版の見出し','修正版の横はみ出しpx','検証の制約'],[[r['locale'],r['status'],r['htmlLang'],'言語一致' if r['locale']==r['htmlLang'] else '指定言語と不一致（修正対象）',by_locale.get(r['locale'],{}).get('locale',''),by_locale.get(r['locale'],{}).get('heading',''),by_locale.get(r['locale'],{}).get('overflow',''),'本番は未認証GET/描画。修正版はlocal、外部通信遮断。実送信・課金未実施。公開後の検証は別。'] for r in signup],[20,15,25,55,25,100,25,125])
    signup_release=read_json(DOCS/'evidence/signup-ci-release.json',{})
    if signup_release:
        sheet(wb,'申込修正のCIと公開状態',['項目','状態・根拠'],[[k,str(v)] for k,v in signup_release.items()],[40,160])
    lab=read_json(DOCS/'evidence/performance-lab.json',{})
    if lab:
        sheet(wb,'性能の追加測定',['取得元','URL','測定日時UTC','Lighthouse版','性能','アクセシビリティ','SEO','LCP ms','TBT ms','CLS','測定条件・制約'],[[r['source'],r['requestedURL'],r['fetchTime'],r['lighthouseVersion'],r['scores'].get('performance'),r['scores'].get('accessibility'),r['scores'].get('seo'),r['metrics']['largest-contentful-paint']['value'],r['metrics']['total-blocking-time']['value'],r['metrics']['cumulative-layout-shift']['value'],r['notes']] for r in lab['reports']],[50,70,35,20,18,23,18,20,20,20,140])
    flows=read_json(DOCS/'evidence/home-to-signup.json',{}).get('results',[])
    if flows:
        sheet(wb,'HOMEから申込24条件',['言語','プラン','請求周期','HOMEリンク','申込HTTP','表示言語','期待合計USD cents','画面表示の合計','金額一致','測定範囲'],[[r['locale'],r['plan'],r['interval'],r['homeLink'],r['status'],r['displayLanguage'],r['expectedTotalUsdCents'],r['formattedTotal'],'合格' if r['totalFound'] else '不合格','Local reviewed HOME → local signup / one Chromium / 外部通信遮断 / 実送信・課金未実施'] for r in flows],[20,25,20,120,20,20,30,35,20,130])
    production_signup=read_json(DOCS/'evidence/home-to-signup-production.json',{})
    if production_signup:
        sheet(wb,'本番HOMEから申込24条件',['言語','プラン','請求周期','HOMEリンク','申込HTTP','表示言語','期待合計USD cents','画面表示の合計','金額一致','測定日時UTC','測定範囲'],[[r['locale'],r['plan'],r['interval'],r['homeLink'],r['status'],r['displayLanguage'],r['expectedTotalUsdCents'],r['formattedTotal'],'合格' if r['totalFound'] else '不合格',production_signup['observedAt'],production_signup['method']] for r in production_signup['results']],[20,25,20,120,20,20,30,35,20,35,130])
    if args.search_console:
        gsc=read_json(args.search_console)
        sheet(wb,'Search Console実データ',['レポート','期間・観測','指標','値','単位','精度','制約','取得日時JST','対象プロパティ'],[[r['report'],r['period'],r['metric'],r['value'],r['unit'],r['precision'],r['limitation'],gsc['observedAtJST'],gsc['property']] for r in gsc['observations']],[40,90,30,100,30,60,140,40,40])
        sheet(wb,'GSC取得範囲と残件',['項目','記録'],[[k,str(v)] for k,v in gsc.items() if k!='observations'],[40,160])
        from openpyxl.drawing.image import Image
        ws=wb.create_sheet('GSC実画面の証跡');ws['A1']='認証済みsimy.oneの実画面。集計日・端末・丸め値・未取得明細はSearch Console実データを参照。私用成果物。'
        for filename,anchor in [('SearchConsole_検索実績.png','A3'),('SearchConsole_CoreWebVitals.png','A56')]:
            file=args.output.parent/filename
            if file.exists():
                img=Image(file);img.height=img.height*1100/img.width;img.width=1100;ws.add_image(img,anchor)
    ai=read_json(DOCS/'evidence/three-ai-review.json',{})
    if ai:
        sheet(wb,'3サービスの実レビュー',['サービス','画面上のモデル表示','実施ラウンド','ペルソナ数','取得方法・自己申告の範囲','限界'],[[r['service'],r['modelLabel'],r['rounds'],r['personas'],r['method'],r['limitation']] for r in ai['services']],[25,60,20,20,130,130])
        sheet(wb,'AI指摘への反論と採否',['ID','論点','初回指摘','ソース照合・反論','最終採否','実装対象','検証','残る未確認'],[[r[k] for k in ['id','issue','initial','counterevidence','decision','scope','verification','remaining']] for r in ai['decisions']],[15,45,120,140,140,65,120,110])
    extra=read_json(DOCS/'evidence/three-ai-browser-followup.json',{})
    if extra:
        sheet(wb,'3AI改善の36表示条件',['ページ','幅CSS px','言語','横はみ出しpx','Windows提供状態','FPの主CTA','ストレージの税注記','測定範囲'],[[r['file'],r['width'],r['locale'],r['overflow'],r.get('windowsNotice',''),r.get('fpHref',''),r.get('storageNote',''),extra['method']] for r in extra['results']],[65,20,20,20,140,80,140,130])
    environment=read_json(DOCS/'evidence/signup-test-environment-discovery.json',{})
    if environment:
        sheet(wb,'テスト環境のソース調査',['項目','確認内容'],[[k,json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v] for k,v in environment.items()],[45,180])
    if args.ai_review:
        actual=read_json(args.ai_review)
        sheet(wb,'実AI回答6件の原文',['サービス','ラウンド','実会話URL（私用）','実回答原文','方法と限界'],[[r['service'],r['round'],r['conversationURL'],r['text'],actual['method']] for r in actual['rounds']],[25,18,100,170,140])
        sheet(wb,'実AIへの共通入力',['ラウンド','実際の入力原文'],[[r['round'],r['text']] for r in actual['prompts']],[20,180])
        persona_rows=[]
        for r in actual['rounds']:
            if r['round']!=1:continue
            text=r['text'];start=text.find('(2)');end=text.find('(3)',start+3)
            assert start>=0 and end>start,(r['service'],'No persona section')
            pieces=re.split(r'(?=[①②③④⑤⑥⑦⑧])',text[start:end])[1:9]
            assert len(pieces)==8 and all(t.startswith(c) for t,c in zip(pieces,'①②③④⑤⑥⑦⑧')),(r['service'],len(pieces))
            persona_rows.extend([[r['service'],i+1,t.strip(),'誰の何の仕事か・AI/人の分担・開始場所・迷いを含む実回答。AI仮説であり実読者の理解率ではない。'] for i,t in enumerate(pieces)])
        sheet(wb,'24ペルソナの実回答',['サービス','ペルソナ番号','ペルソナ別の実回答原文','解釈と限界'],persona_rows,[25,25,180,130])
    production_ai=read_json(DOCS/'evidence/production-three-ai-browser.json',{})
    if production_ai:
        sheet(wb,'本番追加改善の36表示条件',['ページ','幅CSS px','言語','横はみ出しpx','Windows提供状態','FPの主CTA','追加ストレージの税注記','測定範囲'],[[r['file'],r['width'],r['locale'],r['overflow'],r.get('windowsNotice',''),r.get('fpHref',''),r.get('storageNote',''),production_ai['method']] for r in production_ai['results']],[65,20,20,20,140,80,140,130])
    release_ai=read_json(DOCS/'evidence/production-release-three-ai-followup.json',{})
    if release_ai:
        sheet(wb,'追加改善の本番192照合',['ファイル','URL','HTTP','最終URL','レビュー済みソースSHA256','本番SHA256','一致','マージPR','配信Run','取得日時UTC','範囲'],[[r['file'],r['url'],r.get('status',''),r.get('finalURL',''),r.get('expectedSha256',''),r.get('actualSha256',''),r['matches'],release_ai['pullRequest'],release_ai['deploymentRun'],release_ai['observedAt'],release_ai['scope']] for r in release_ai['results']],[70,100,15,100,75,75,15,100,100,35,130])
    win_status=read_json(DOCS/'evidence/windows-distribution-status.json',{})
    if win_status:
        sheet(wb,'本番Windows提供の一次情報',['項目','確認内容'],[[k,json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v] for k,v in win_status.items()],[45,170])
    if args.gsc_export:
        original=load_workbook(args.gsc_export,data_only=True)
        tabs={'平均読み込み時間のチャート':'GSC公式_日別92日','クエリ':'GSC公式_クエリ1000件','ページ':'GSC公式_ページ359件','国':'GSC公式_国207件','デバイス':'GSC公式_端末3種','検索での見え方':'GSC公式_検索での見え方','フィルタ':'GSC公式_フィルタ'}
        for source in original:
            values=list(source.values)
            sheet(wb,tabs.get(source.title,'GSC公式_'+source.title),list(values[0]),[list(r) for r in values[1:]],[100]+[25]*(source.max_column-1))
        daily=list(original.worksheets[0].values)[1:]
        clicks=sum(r[1] for r in daily);impressions=sum(r[2] for r in daily)
        sheet(wb,'GSC公式_基準値と母集団',['項目','値・制約'],[['期間',str(daily[0][0])+'〜'+str(daily[-1][0])],['日数',len(daily)],['クリック合計',clicks],['表示回数合計',impressions],['CTR（合計から計算・%）',clicks/impressions*100],['対象','sc-domain:simy.one ドメイン全体。現行199 HTML / index159とは母集団が異なる'],['クエリ制約','公式exportの上位1000件。匿名化等による未掲載があり日別合計と単純一致しない'],['日別の元シート名','平均読み込み時間のチャート。元Excelの列は日付/クリック数/表示回数/CTR/掲載順位。速度測定値として扱わない'],['因果','今回の改修前の基準値。成果・順位改善の立証ではない']],[50,170])
        opportunity=sorted([r for r in list(original['ページ'].values)[1:] if r[2]>=1000 and r[3]<0.01],key=lambda r:-r[2])
        sheet(wb,'GSC公式_次回の確認候補',['URL','クリック','表示回数','CTR（export値）','掲載順位','抽出条件','次の確認・限界'],[[*r,'表示1000以上かつCTR1%未満。便宜的な調査候補で合否基準ではない','実クエリの意図・言語・検索結果とtitle/descriptionを照合。低CTRだけで誤りや改善効果を断定しない。'] for r in opportunity],[110,20,25,30,25,120,150])
    history_counts=history_sheets(wb,read_json(args.history)) if args.history else {}
    if args.history:
        ws=wb['はじめに'];ws.append(['履歴付きの私用版','このファイルは取得した過去会話の原文を含む私用成果物。公開リポジトリへ掲載しない。機密値は保守的に省略。候補抽出は機械的な整理で、全発言の要件確定や実装充足を意味しない。'])
    if LONG_TEXT:
        sheet(wb,'長文セルの全文',['参照ID','元シート','元の行','元の列','分割番号','分割総数','全文の分割（順に連結）'],list(LONG_TEXT),[18,35,15,15,15,15,150])
    args.output.parent.mkdir(parents=True,exist_ok=True);wb.save(args.output)
    check=load_workbook(args.output,data_only=False)
    assert check['全199ページ'].max_row==200
    assert check['専門家50視点'].max_row==51
    assert check['ページ別検査'].max_row==len(inventory)*12+1
    assert check['指摘一覧'].max_row==len(findings)+1
    assert check['概要']['F2'].value.startswith('=COUNTIF')
    print(json.dumps({'output':str(args.output),'sheets':len(check.sheetnames),'findings':len(findings),'pages':len(inventory),'checks':len(checks),'experts':50,'browserCases':len(browser_rows),'bytes':args.output.stat().st_size,**history_counts},ensure_ascii=False))

if __name__=='__main__':main()
