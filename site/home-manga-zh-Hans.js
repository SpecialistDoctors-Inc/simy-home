/* Preview stories reuse the existing accessible tab controls. */
Object.assign(scenarios, {
 codex:{source:"交代客户回复任务",prompt:"准备一份客户回复。根据资料核实事实，发送前给我确认。",acknowledgement:"已核对资料并准备好回复草稿，请确认内容。",workflow:"准备客户回复",steps:[["根据资料核实事实",'Done'],["起草回复",'Done'],["你确认内容",'Waiting'],["应用修改",'Next']],output:"请确认草稿的事实与表述，尚未发送。"},
 claude:{source:"整理会议后的行动",prompt:"整理会议决定和每个人的下一步，标出不明确的事项。",acknowledgement:"已整理决定和负责人，请确认尚未指定负责人的任务。",workflow:"整理会后行动",steps:[["核对会议记录",'Done'],["整理决定和下一步",'Done'],["确认未定的负责人",'Waiting'],["落实必要修改",'Next']],output:"请确认未定负责人和下一步。"},
 cowork:{source:"准备下一个客户的回复",prompt:"为下一个客户准备回复，也加入相同的检查。",acknowledgement:"草稿已准备，包含事实核查和发送前确认。",workflow:"下次沿用相同检查",steps:[["选择类似工作的流程",'Done'],["核查事实并起草",'Done'],["你确认内容",'Waiting'],["落实必要修改",'Next']],output:"已加入上次的检查，请确认草稿内容。"}
});
for(const [key,label] of Object.entries({codex:"客户回复",claude:"会议后续",cowork:"下一项类似工作"}))document.querySelector(`[data-scenario="${key}"]`).textContent=label;
const baseRender=renderScenario;
renderScenario=function(name){baseRender(name);document.querySelectorAll("[data-step-status]").forEach(e=>{e.textContent=({done:"已完成",waiting:"等待你处理",next:"确认后",ready:"确认后"})[e.dataset.status]||e.textContent});document.querySelector(".demo-workflow-head>.status").textContent="待确认"};
renderScenario("codex");
