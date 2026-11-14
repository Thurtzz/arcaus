/* Approved ARCAUS image-locked hero with REAL UI and evidence-backed actions.
 * Does not contact Gemini or expose keys. Browser routes work in static bundle mode.
 */
(function(){
 const $=s=>document.querySelector(s);
 const ref=$('.reference-stage'),modal=$('#referenceDialog'),title=$('#referenceDialogTitle'),content=$('#referenceDialogContent'),link=$('#referenceDialogLink');
 const visibleHref={};
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 function show(heading,body,target='#data',label='Explore the evidence ↗'){
  title.textContent=heading;content.innerHTML=body;link.href=target;link.textContent=label;
  if(typeof modal.showModal==='function')modal.showModal();else modal.setAttribute('open','');
 }
 function navigateStudy(id){const b=$(`[data-featured="${id}"]`);if(b)b.click();else location.hash='experiments';}
 function navigateComparison(id){const b=$(`[data-feature-comparison="${id}"]`);if(b)b.click();else location.hash='findings';}
 ref.querySelectorAll('[data-ref-study]').forEach(b=>b.addEventListener('click',()=>navigateStudy(b.dataset.refStudy)));
 ref.querySelectorAll('[data-ref-comparison]').forEach(b=>b.addEventListener('click',()=>navigateComparison(b.dataset.refComparison)));
 ref.querySelectorAll('[data-ref-thickness]').forEach(b=>b.addEventListener('click',()=>{
   const t=b.dataset.refThickness,s=window.ARCAUS_DATA_STATE?.data?.bass2?.summary;
   const n=Number(s?.median_test_mean_spread_by_thickness_mm_s?.[t+'.0']);
   const v=Number.isFinite(n)?n.toFixed(4):'not available';
   show(`${t} mm PMMA · verified NASA observation`,`<p>Median across test-run mean flame spread rates at <strong>${t} mm PMMA</strong>: <strong>${v} mm/s</strong>.</p><p>This is descriptive BASS-II test data from NASA/TM-20210011385 Table 5.1, not a predicted flame behavior, general safety limit, or combined cross-study curve.</p><p><a href="https://ntrs.nasa.gov/citations/20210011385" target="_blank" rel="noopener noreferrer">Read the NASA source ↗</a></p>`);
 }));
 ref.querySelector('[data-ref-action="artwork"]').addEventListener('click',()=>show('The flame is an illustration','<p>The glowing spherical flame is <strong>original illustrative artwork</strong> representing the theme of microgravity combustion. It is not NASA footage, an experiment-specific image, or a physical simulation.</p><p>Explore real NASA-sourced findings from BASS-II, Saffire-V, and SoFIE-GEL in the investigation archive.</p>','#experiments','Explore experiments ↗'));
 ref.querySelector('[data-ref-action="integrity"]').addEventListener('click',()=>{const st=window.ARCAUS_DATA_STATE;
  const m=st?.data?.manifest,c=st?.data?.consistency,passed=c?.checks_passed??c?.passed,failed=c?.checks_failed??c?.failed;
  show('Evidence provenance & status',`<p><strong>${st?.live?'Live research API connected':'Verified static NASA evidence bundle'}</strong></p><p>Bundle SHA-256 prefix: <strong>${escape(m?.content_sha256?.slice(0,12)||'unavailable')}</strong><br/>Consistency checks: <strong>${escape(passed??'unavailable')} passed / ${escape(failed??'unavailable')} failed</strong>.</p><p>Findings distinguish verified measurements, NASA author conclusions and untested hypotheses. ARCAUS is independent and is not a NASA-operated service.</p>`,'#method','Read research methodology ↗');
 });
 function update(){const st=window.ARCAUS_DATA_STATE;if(!st||!st.data)return;const c=st.data.consistency||{},bad=(c.checks_failed??c.failed??0)>0;
  const originalSha='7829520c83d7';const currentSha=st.data.manifest?.content_sha256?.slice(0,12)||'';
  $('.ref-status').classList.toggle('state-notice',bad||st.live||currentSha!==originalSha);
  $('#refBundleMode').textContent=bad?'EVIDENCE CHECK FAILED':st.live?'VERIFIED API CONNECTED':'VERIFIED STATIC BUNDLE';
  $('#refBundleHash').textContent='SHA: '+(st.data.manifest?.content_sha256?.slice(0,12)||'unavailable');
 }
 window.ARCAUS_ReferenceUpdate=update;
 let retries=0;const check=()=>{update();if(!window.ARCAUS_DATA_STATE&&retries++<15)setTimeout(check,180)};check();
 const top=$('.return-top');let active=false;
 function onScroll(){const sc=window.scrollY>700;if(active!==sc){active=sc;top.classList.toggle('visible',sc);}}
 window.addEventListener('scroll',onScroll,{passive:true});onScroll();
})();
