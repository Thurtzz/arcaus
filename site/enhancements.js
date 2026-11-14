/* ARCAUS supplemental widgets: no secrets, evidence only. */
(function(){
 const h=(txt)=>String(txt??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const $=id=>document.getElementById(id);
 function statusFrom(data,live){const z=data.consistency||{};return {pass:z.checks_passed??z.passed,fail:z.checks_failed??z.failed,hash:data.manifest?.content_sha256?.slice(0,12),mode:live?'VERIFIED API CONNECTED':'VERIFIED STATIC BUNDLE'};}
 window.renderArcausEnhancements=function(view){
  const {data,live,base}=view;const summary=data.bass2.summary;const runs=data.bass2.pmma_tests;const {pass,fail,hash,mode}=statusFrom(data,live);
  const os=runs.map(x=>x.o2_initial_vol_pct).filter(Number.isFinite);const fs=runs.flatMap(x=>[x.velocity_min_cm_s,x.velocity_max_cm_s]).filter(Number.isFinite);
  const vals=[
   [summary.pmma_tests_with_spread,'PMMA TESTS'],
   [summary.pmma_spread_steps,'TRACKED STEPS'],
   [os.length?`${Math.min(...os).toFixed(1)}–${Math.max(...os).toFixed(1)}%`:'—','O₂ INITIAL'],
   [fs.length?`${Math.min(...fs)}–${Math.max(...fs)} cm/s`:'—','FLOW RANGE']
  ];
  if($('heroReadouts'))$('heroReadouts').innerHTML=vals.map(([v,l])=>`<span class="hero-readout"><strong>${h(v)}</strong><small>${h(l)}</small></span>`).join('');
  if($('heroChecks'))$('heroChecks').textContent=fail===0?`${pass} CHECKS PASSED`:`INTEGRITY: ${fail??'UNKNOWN'} FAILED`;
  if($('footerBundleStatus'))$('footerBundleStatus').textContent=`${mode} · SHA ${hash||'UNAVAILABLE'}`;
  // complete catalog - source identifiers in original evidence bundle
  if($('sourceLibrary'))$('sourceLibrary').innerHTML=data.sources.map(s=>`<div class="source-row"><a class="source-link" href="${h(s.url)}" target="_blank" rel="noopener noreferrer">${h(s.title)} ↗</a><small>${h(s.publisher||'NASA research source')} · ${h(s.year||'')} · ${h(s.access||'source')}</small><p>${h(s.access_note||'')}</p></div>`).join('');
  const ask=$('askArcaus');if(!ask)return;
  ask.hidden=!live;
  if(!live)return;
  const button=$('askButton'),input=$('askQuestion'),message=$('askStatus'),result=$('askResult');
  async function onAsk(){const q=input.value.trim();if(!q){message.textContent='Enter a research question first.';return;}
   button.disabled=true;message.textContent='Retrieving NASA evidence and requesting a grounded explanation…';result.innerHTML='';
   try{const response=await fetch(`${base}/ask?${new URLSearchParams({q})}`,{cache:'no-store'});
    const body=await response.json();if(!response.ok)throw new Error(body.error?.message||`HTTP ${response.status}`);
    const d=body.data||{};
    const cite=Array.isArray(d.citations)?d.citations:[];
    result.innerHTML=`<div class="ask-answer"><p>${h(d.answer||(d.supported?'No explanation provided.':'The retrieved evidence cannot verify an answer to that question.'))}</p><div class="micro-caption">${d.supported?'SUPPORTED BY RETRIEVED EVIDENCE':'UNSUPPORTED OR NOT ENOUGH EVIDENCE'} · ${h(body.meta?.grounding||'unverified')}</div></div>`+cite.map(c=>`<div class="ask-citation"><strong>${h(c.id)} · ${h(c.evidence_class||c.evidence_type)}</strong><p>${h(c.statement)}</p><small>${h(typeof c.conditions==='object'?JSON.stringify(c.conditions):c.conditions)}</small>${(c.sources||[]).map(s=>`<div><a href="${h(s.url)}" target="_blank" rel="noopener noreferrer">${h(s.title||'Original NASA source')} · ${h(s.locator||'')} ↗</a></div>`).join('')}</div>`).join('');
    message.textContent=d.supported?'Grounded response returned. Check cited evidence before relying on the explanation.':'Not enough evidence to support that answer.';
   }catch(e){message.textContent=`Ask ARCAUS is not available: ${e.message}. The verified evidence explorer still works.`;}
   finally{button.disabled=false;}
  }
  button.addEventListener('click',onAsk);input.addEventListener('keydown',e=>{if(e.key==='Enter')onAsk();});
 };
})();
