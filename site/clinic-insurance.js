(function(global){
 'use strict';
 // The distribution URL carries the presentation setting through to PDF export.
 const enabled=()=>new URLSearchParams(global.location?.search||'').get('insurance')!=='off';
 if(global.document)global.document.documentElement.dataset.clinicInsurance=enabled()?'on':'off';
 global.SimyClinicInsurance={enabled};
})(typeof window==='undefined'?globalThis:window);
