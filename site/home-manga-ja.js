/* Preview stories reuse the existing accessible tab controls. */
Object.assign(scenarios, {
 codex:{source:'顧客への返信を頼む',prompt:'お客様への返事を準備して。資料で事実を確かめ、送る前に見せて。',acknowledgement:'資料を確認し、返信の下書きを準備しました。内容の確認をお願いします。',workflow:'顧客への返信を準備',steps:[['資料で事実を確認','Done'],['返信を下書き','Done'],['あなたが内容を確認','Waiting'],['修正を反映','Next']],output:'下書きの事実と表現を確認してください。送信はまだ行っていません。'},
 claude:{source:'会議の次の行動を整理',prompt:'この会議で決めたことと、次に誰が何をするかを整理して。不明な点は確認して。',acknowledgement:'決定事項と担当者を整理しました。担当が決まっていない項目を確認してください。',workflow:'会議後の行動を整理',steps:[['会議の記録を確認','Done'],['決定と次の行動を整理','Done'],['未確定の担当を確認','Waiting'],['必要な修正を反映','Next']],output:'未確定の担当と、次の行動を確認してください。'},
 cowork:{source:'次の顧客への返信を頼む',prompt:'次のお客様への返事も、同じ確認を入れて準備して。',acknowledgement:'今回も事実確認と送信前の確認を入れて、下書きを準備しました。',workflow:'いつもの確認を次にも活かす',steps:[['似た仕事の手順を選ぶ','Done'],['事実確認と下書き','Done'],['あなたが内容を確認','Waiting'],['必要な修正を反映','Next']],output:'前回と同じ確認が入っています。下書きの内容を確認してください。'}
});
for(const [key,label] of Object.entries({codex:'顧客への返信',claude:'会議のフォロー',cowork:'次の似た仕事'}))document.querySelector(`[data-scenario="${key}"]`).textContent=label;
const baseRender=renderScenario;
renderScenario=function(name){baseRender(name);document.querySelectorAll('[data-step-status]').forEach(e=>{e.textContent=({done:'完了',waiting:'あなたの確認待ち',next:'確認後',ready:'確認後'})[e.dataset.status]||e.textContent});document.querySelector('.demo-workflow-head>.status').textContent='確認待ち'};
renderScenario('codex');
