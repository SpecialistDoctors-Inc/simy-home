(function(global){
'use strict';
function model(report){
  const findings=(report.findings||[]).filter(f=>/^(seo|geo)-/.test(f.id));
  const find=pattern=>findings.find(f=>pattern.test(f.id+' '+f.title));
  const title=find(/seo-title|検索結果の見出し/);
  const description=find(/description|ページの説明文/);
  const heading=find(/heading|主な見出し|seo-h1/);
  const schema=find(/structured|JSON|機械に伝える/);
  const observed=f=>f?.state==='observed';
  const value=f=>observed(f)?String(f.evidence||'').trim():'';
  const t=value(title),d=value(description),h=value(heading);
  const name=t.split(/[｜|]/)[0].trim()||new URL(report.url).hostname;
  const questions=[
    {question:'どんな診療を受けられますか',pattern:/小児科|内科|外科|皮膚科|歯科|眼科|胃カメラ|大腸カメラ|内視鏡|健診|予防接種/},
    {question:'どの地域にあり、どう通えますか',pattern:/駅|徒歩|アクセス|[都道府県市区町村]/},
    {question:'医師の専門性は分かりますか',pattern:/専門医|認定医|資格|専門|指導医/},
    {question:'費用はどこで分かりますか',pattern:/費用|料金|[0-9０-９]+円/},
    {question:'受診・予約はどう始めますか',pattern:/予約|電話|受付|受診方法/}
  ].map(q=>({...q,answer:(q.question.includes('通え')&&d.match(/[^。]*(?:駅|徒歩)[^。]*(?:。|$)/)?.[0])||(d||t).match(new RegExp('[^。]*(?:'+q.pattern.source+')[^。]*(?:。|$)'))?.[0]||'',status:q.pattern.test(t+' '+d)?'案内あり':'本文を確認'}));
  const priorities=[];
  if(!d)priorities.push({title:'検索結果に出す紹介文を整えます',detail:'取得したトップページで説明文を確認できませんでした。診療内容・所在地・受診方法をまとめ、来院を検討する方への紹介文を作成します。'});
  const repeated=h.length>10&&h.slice(0,Math.floor(h.length/2)).trim()===h.slice(Math.ceil(h.length/2)).trim();
  if(repeated)priorities.push({title:'冒頭の見出しで、診療内容まで伝えます',detail:'取得した主見出しは同じ医院名の繰り返しです。PC・スマートフォン用の表示が重複している可能性もあります。見える画面を確認し、地域と診療内容が分かる見出しに整えます。'});
  const gaps=questions.filter(q=>q.status!=='案内あり');
  if(gaps.length&&d)priorities.push({title:'初めての方の疑問を、受診前に解消します',detail:'検索向けの見出し・説明文では「'+gaps.map(q=>q.question.replace('？','')).join('」「')+'」の回答を読み取れませんでした。診療案内や予約ページの説明を確認し、必要な案内を入口にまとめます。'});
  if(!priorities.length&&d)priorities.push({title:'すでに伝わっている内容を、受診への入口につなげます',detail:'検索向けの紹介には診療内容が記載されています。その内容をトップの説明にも活かし、診療案内・受診方法へ進める構成を試せます。'});
  const strengths=questions.filter(q=>q.status==='案内あり'&&q.answer).slice(0,3).map(q=>({title:q.question,detail:q.answer}));
  const count=questions.filter(q=>q.status==='案内あり').length;
  const proposalHeading=t.includes('｜')?t.split('｜').slice(1).join('｜')+'。'+name:name+'。'+t;
  const proposalDescription=d.split('。').filter(Boolean).slice(0,3).join('。')+(d?'。':'');
  const countSchema=value(schema).match(/(?:JSON-LD[：:]?\s*|[：:]\s*)(\d+)件/)?.[1];
  return {name,strengths,available:findings.length>0,scope:'取得したトップページの見出し・検索向け説明・構造化データを使用',intro:d||t||'医院の特徴を判断できる説明を、今回の取得情報から読み取れませんでした。',metrics:[['紹介文で答えられる疑問',count+' / 5'],['検索向け見出し',t?Array.from(t).length+'文字':'取得できず'],['検索向け説明文',d?Array.from(d).length+'文字':'取得できず']],questions,priorities:priorities.slice(0,3),before:h||t||'取得した見出しなし',proposal:{heading:t?proposalHeading:name,description:proposalDescription,button:'診療内容・受診方法を見る'},schema:countSchema,checkedAt:report.checkedAt};
}
global.SimyClinicGrowth={model};
})(typeof window==='undefined'?globalThis:window);
