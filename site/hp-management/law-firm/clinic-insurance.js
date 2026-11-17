(function(global){
 'use strict';
 // Temporarily pause insurance referrals on the site, portal, and reports.
 const enabled=()=>false;
 if(global.document)global.document.documentElement.dataset.clinicInsurance=enabled()?'on':'off';
 global.SimyClinicInsurance={enabled};
})(typeof window==='undefined'?globalThis:window);
