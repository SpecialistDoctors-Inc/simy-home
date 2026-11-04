(function(global){
'use strict';
function model(report){
 const g=report.growth, a=g?.status==='assessed'?g.analysis:null;
 const pages=Array.isArray(g?.sources)?g.sources:[];
 const name=a?.clinicName||new URL(report.url).hostname;
 if(!a)return {name,available:false,scope:'集客分析を完了できませんでした。セキュリティの結果は上に表示しています。',metrics:[],questions:[],priorities:[],strengths:[]};
 const questions=a.questions.map(q=>({...q,status:q.status==='found'?'案内あり':'今回の範囲では見つからず'}));
 return {name,available:true,headline:a.headline,intro:a.summary,scope:pages.length+'ページの公開本文を分析。表示・検索順位・集患数の評価ではありません。',sources:pages,metrics:[['本文を読んだページ',pages.length+'ページ'],['受診前の疑問への案内',a.questions.filter(q=>q.status==='found').length+' / 5'],['優先して変えたいこと',a.priorities.length+'件']],strengths:a.strengths,questions,priorities:a.priorities,proposal:{heading:a.proposal.heading,description:a.proposal.body,button:a.proposal.button},checkedAt:report.checkedAt};
}
global.SimyClinicGrowth={model};
})(typeof window==='undefined'?globalThis:window);
