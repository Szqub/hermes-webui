(()=>{
function mk(groups){const sel=new Element('select');for(const [prov,vals] of groups){const g=sel.appendChild(new Element('optgroup'));g.dataset.provider=prov;for(const v of vals){const o=g.appendChild(new Element('option'));o.value=v;o.dataset.provider=prov;}}return sel;}
const out={};
let sel;
// 1. Custom group (non-reserved config) advertising @custom:qwen3:8b: what state does a pick yield?
sel=mk([['openai',['gpt-4o']],['custom',['@custom:qwen3:8b','@custom:mistral']]]);
out.pickColon=_modelStateForSelect(sel,'@custom:qwen3:8b');
out.pickPlain=_modelStateForSelect(sel,'@custom:mistral');
// 2. reserved option picks
sel=mk([['lmstudio',['llama3']],['custom',['@!:qwen3:8b','@!:vendor/x:y']]]);
out.pickReserved=_modelStateForSelect(sel,'@!:qwen3:8b');
out.pickReserved2=_modelStateForSelect(sel,'@!:vendor/x:y');
// 3. restore bare model with custom hint into a select with reserved option
out.findBareCustom=_findModelInDropdown('qwen3:8b',sel,'custom');
out.findReserved=_findModelInDropdown('@!:qwen3:8b',sel,'lmstudio');
out.findReservedNoHint=_findModelInDropdown('@!:qwen3:8b',sel,null);
// 4. hint must not reinterpret qualified value: various hints
const hints=[null,'','custom','custom:qwen3','lmstudio','openai','@!'];
out.ensureMatrix={};
for(const v of ['@!:qwen3:8b','@custom:qwen3:8b','@openai:gpt-4o','@custom%3Aeast%3Awest:a:b','@nous:x']){
  out.ensureMatrix[v]=hints.map(h=>{const s=mk([]);const a=_ensureModelOptionInDropdown(v,s,h);return [h,a,_modelStateForSelect(s,s.value)];});
}
// 5. cross-provider substitution through normalized fallback: case/dash differences
sel=mk([['custom',['@!:Qwen3-8B']],['openai',['gpt-4o']]]);
out.normSub1=_findModelInDropdown('@openai:qwen3.8b',sel,'openai');
out.normSub2=_findModelInDropdown('@custom:backup:qwen3-8b',sel,'custom');
out.normSub3=_findModelInDropdown('@!:qwen3.8b',sel,'custom');
sel=mk([['openai',['gpt-4o']],['azure',['@azure:gpt-4o']]]);
out.normSub4=_findModelInDropdown('@azure:GPT-4o',sel,'openai');
out.normSub5=_findModelInDropdown('@openai:gpt-4o',sel,'azure');
// 6. slash-qualified vendor ids (explicitProvider?) across providers
sel=mk([['openrouter',['anthropic/claude-x']],['custom',['@!:anthropic/claude-x']]]);
out.slash1=_findModelInDropdown('@!:anthropic/claude-x',sel,'openrouter');
out.slash2=_findModelInDropdown('@openrouter:anthropic/claude-x',sel,'custom');
// 7. dedup
sel=mk([['custom',['@!:qwen3:8b','@!:qwen3:8b','qwen3:8b']],['custom:qwen3',['@custom:qwen3:8b']]]);
out.dedupRemoved=_deduplicateModelPickerOptions(sel,'@!:qwen3:8b');
out.dedupLeft=sel.options.map(o=>[o.value,o.dataset.provider]);
// 8. labels / bare names / badge eq
out.label=getModelLabel('@!:qwen3:8b');
out.bare=_modelBareNameForProvider('@!:qwen3:8b','custom');
out.badge=_isEquivalentConfiguredModelEntry('@!:qwen3:8b',{provider:'custom'},[{value:'qwen3:8b',providerId:'custom'}]);
out.badgeCross=_isEquivalentConfiguredModelEntry('@!:qwen3:8b',{provider:'custom'},[{value:'8b',providerId:'custom:qwen3'}]);
// 9. alias
out.alias=['qwen3:8b','@!:qwen3:8b','custom/qwen3:8b'].map(t=>_resolveModelAliasTarget([{value:'@!:qwen3:8b',provider:'custom'},{value:'@custom:qwen3:8b',provider:'custom:qwen3'}],{},t));
return out;})()
