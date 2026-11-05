import json
from pathlib import Path
p=Path('site/clinic-ai-observations.js')
s=json.loads(p.read_text().split('=',1)[1].strip().rstrip(';'))
a=s[0]
a['version']=2
a['sourceUrl']='https://agent.tinyfish.ai/runs/d84a9f71-f6fb-47de-b527-1ecb1cdc1cdc'
a['captureNote']='2026年11月5日に別途取得。英語UIのGoogleアカウントで日本語の質問を入力。各質問1件の有効なAIモード回答を採用。5歳児健診はモード確認を伴う再取得を採用し、初回の不確かな取得は集計から除外。'
a['startedAt']='2026-11-05'
a['finishedAt']='2026-11-05'
# The source reports did not supply exact wall-clock timestamps. Preserve date precision rather than invented time.
a['datePrecision']='day'
queries=[('感染に配慮した予防接種','神谷町で赤ちゃんの予防接種を受けたい。風邪の子と時間を分けている小児科は？',True,[],'https://urachil.com/access.html'),('成長・内分泌の専門相談','港区で子どもの身長の伸びが気になる。内分泌の専門医に相談できるクリニックは？',False,['浦上小児内分泌・糖尿病クリニック','東京豪徳寺成長クリニック','八丁堀3丁目クリニック'],None),('学校の心電図の異常','神谷町で子どもの心臓や学校の心電図の異常を相談できるクリニックは？',True,[],'https://urachil.com/'),('日曜午前の小児科','虎ノ門の近くで日曜日の午前に診てもらえる小児科を教えて。',True,['赤坂おだやかクリニック'],'https://urachil.com/'),('5歳児健診の予約','神谷町で5歳児健診を受けたい。どこで予約できる？',True,['有明みんなクリニック 田町芝浦院'],'https://urachil.com/'),('初めての予防接種','神谷町で初めて子どもの予防接種を予約したい。持ち物と予約方法が分かる医院は？',True,[],'https://urachil.com/')]
a['questions']=[dict(theme=t,query=q,status='observed',mentioned=m,officialCitation='verified' if u else 'not_observed',peers=peers,differentDomainLinks=[],**({'verifiedDestination':u} if u else {}),**({'sourceUrl':'https://agent.tinyfish.ai/runs/5acfe097-bf73-4636-b11f-4d11ff591b57'} if i==4 else {})) for i,(t,q,m,peers,u) in enumerate(queries)]
a['journeyAudit']={
 'version':1,'checkedOn':'2026-11-05','pagesRead':12,
 'headline':'専門性を知ってから、適切な予約先までつなげる。',
 'summary':'日曜診療・予防接種・心臓の相談ではAI検索で紹介を確認。次は、成長相談の専門性、担当医・担当日、目的に合う予約枠を一緒に伝えることを優先します。',
 'scope':'公式サイトのトップと主要11ページ、予約画面の公開部分、Google AIモードの回答を別途確認。予約確定・ログイン後・スマートフォン表示は未検証。診断のたびに自動実測した結果ではありません。',
 'sourceUrl':'https://agent.tinyfish.ai/runs/4971cb9c-14b0-4fa7-83ce-22be70bb787e',
 'findings':[
 {'id':'doctor-schedule','priority':'最優先','title':'専門的な相談を、担当医と予約につなげる','observation':'医師紹介は「担当医のお知らせ」を案内していますが、リンク先に「記事がありません」と表示されています。','impact':'専門分野を知っても、誰の担当日に予約すればよいか判断できません。','change':'専門分野・担当医・担当日・選ぶ予約枠を一緒に掲載し、案内先を復旧します。','sources':[{'label':'医師紹介','url':'https://urachil.com/doctor.html'},{'label':'担当医のお知らせ','url':'https://urachil.com/'}]},
 {'id':'growth-discovery','priority':'高','title':'身長・成長の相談先として伝える','observation':'低身長・内分泌疾患を得意とする医師の記載があります。一方、今回の「内分泌の専門医」を探すAI回答にはうらちるが登場しませんでした。','impact':'一般の小児科として見つかることと、専門的な悩みの相談先として見つかることに差があります。','change':'成長相談のページに、相談できる悩み・担当医・担当日・持ち物・予約方法をまとめます。検索結果の原因や改善効果を断定するものではありません。','sources':[{'label':'医師紹介','url':'https://urachil.com/doctor.html'},{'label':'AI検索の取得記録','url':a['sourceUrl']}]},
 {'id':'booking-categories','priority':'高','title':'予約ボタンの前に、選ぶ予約枠を伝える','observation':'クリーンタイムと5歳児健診には、通常の健診・予防接種とは別の予約枠があります。5歳児健診の専用枠の案内はトップにあり、乳幼児健診ページには見つかりませんでした。','impact':'WEB予約に進めても、目的に合う枠を選ぶために別ページの情報が必要です。','change':'各診療ページの予約ボタン直前に、選ぶ枠の名称と注意点を掲載します。学校健診の異常を指摘された場合の「一般小児科」への案内も添えます。','sources':[{'label':'乳幼児健診','url':'https://urachil.com/infants.html'},{'label':'予約画面の確認記録','url':'https://agent.tinyfish.ai/runs/4971cb9c-14b0-4fa7-83ce-22be70bb787e'}]},
 {'id':'ai-accuracy','priority':'中','title':'AIの持ち物案内を、公式の最新情報と照合する','observation':'今回のAI回答は「健康保険証」を案内。公式の来院案内は「マイナ保険証もしくは資格確認書」と記載しています。','impact':'医院が紹介されても、保護者が古い持ち物案内を受け取ることがあります。','change':'公式ページの持ち物表記をそろえ、予約前に最新案内を確認できるようにします。修正後もAI回答を再測定します。','sources':[{'label':'来院案内','url':'https://urachil.com/visitor.html'},{'label':'AI回答の取得記録','url':a['sourceUrl']}]}
 ],
 'confirmed':['予防接種ページに自費料金表があります。','来院案内に初診・予防接種・健診の持ち物があります。','WEB予約への入口と、目的別の予約項目があります。'],
 'proposal':{'heading':'お子さんの身長の伸びが気になったら。神谷町で相談できる小児科です。','body':'うらちるクリニックでは、低身長・内分泌疾患を得意とする医師が診療しています。担当医・担当日・ご予約方法をご案内します。','button':'成長相談の担当医・予約方法を見る','note':'新しい成長相談ページの掲載案です。掲載前に、担当日と予約方法を医院でご確認ください。'}
}
p.write_text('/* Dated observations; never substitute these for a new or different-site search. */\nwindow.SimyClinicAiObservations='+json.dumps(s,ensure_ascii=False,indent=2)+';\n')
