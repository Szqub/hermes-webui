(()=>{
function mk(groups){const sel=new Element('select');for(const [prov,vals] of groups){const g=sel.appendChild(new Element('optgroup'));g.dataset.provider=prov;for(const v of vals){const o=g.appendChild(new Element('option'));o.value=v;o.dataset.provider=prov;}}return sel;}
const out={};
let sel=mk([['safe',['@safe:model-a']],['custom',['@!:model-a']]]);
out.dupApplied=_ensureModelOptionInDropdown('@safe:model-a',sel,'custom');
out.dupOpts=sel.options.map(o=>[o.value,o.dataset.provider]);
out.dupState=_modelStateForSelect(sel,sel.value);
out.dedupAfter=_deduplicateModelPickerOptions(sel,sel.value);
out.dupOpts2=sel.options.map(o=>[o.value,o.dataset.provider]);
// legacy unescaped non-custom colon provider: does the hint interpret it?
out.legacyHint=[null,'a','a:b','x'].map(h=>{const s=mk([]);const v=_ensureModelOptionInDropdown('@a:b:c',s,h);return [h,v,_modelStateForSelect(s,s.value)];});
out.parseHint=[null,'a:b'].map(h=>_parseModelRoute('@a:b:c',h));
// group metadata hint in state
sel=mk([['a:b',['@a:b:c']]]);out.stateGroupAB=_modelStateForSelect(sel,'@a:b:c');
sel=mk([['a',['@a:b:c']]]);out.stateGroupA=_modelStateForSelect(sel,'@a:b:c');
// reserved catalog option seeding: live models for custom provider
window._activeProvider='lmstudio';
sel=mk([['custom',['@!:qwen3:8b']]]);
_addLiveModelsToSelect('custom',[{id:'qwen3:8b'},{id:'mistral:7b'}],sel);
out.liveOpts=sel.options.map(o=>[o.value,o.dataset.provider]);
out.liveStates=sel.options.map(o=>_modelStateForSelect(sel,o.value));
return out;})()
