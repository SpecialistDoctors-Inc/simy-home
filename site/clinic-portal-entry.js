(function(global){
 const endpoint=global.document.querySelector('#diagnosis-form')?.dataset.endpoint;if(!endpoint)return;
 const service=new URL(endpoint).origin;
 function go(value){const u=new URL('/clinic-portal',service);if(value)u.searchParams.set('target',value);global.location.assign(u.href);}
 global.document.addEventListener('submit',event=>{const f=event.target;if(global.SimyClinicPortal||!f.matches('#rebuild-form,[data-report-rebuild]'))return;event.preventDefault();event.stopImmediatePropagation();go(f.querySelector('[name=url]')?.value||global.document.querySelector('#diagnosis-url')?.value||'');},true);
})(window);
