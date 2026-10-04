(()=>{
function mk(groups){const sel=new Element('select');for(const [prov,vals] of groups){const g=sel.appendChild(new Element('optgroup'));g.dataset.provider=prov;for(const v of vals){const o=g.appendChild(new Element('option'));o.value=v;o.dataset.provider=prov;}}return sel;}
const out={};
let sel=mk([['custom',['@custom:qwen3:8b','@custom:llama3.1:8b','@custom:gemma2:9b']]]);
out.ids=sel.options.map(o=>_modelPickerOptionIdentity(o.value,_getOptionProviderId(o)));
out.removed=_deduplicateModelPickerOptions(sel,'');
out.left=sel.options.map(o=>o.value);
sel=mk([['custom',['qwen3:8b','llama3.1:8b']]]);
out.removedBare=_deduplicateModelPickerOptions(sel,'');
out.leftBare=sel.options.map(o=>o.value);
sel=mk([['custom:lab',['@custom:lab:qwen3:8b','@custom:lab:llama3.1:8b']]]);
out.removedNamed=_deduplicateModelPickerOptions(sel,'');
out.leftNamed=sel.options.map(o=>o.value);
// ensure path dedupe from picking
sel=mk([['custom',['@custom:qwen3:8b','@custom:llama3.1:8b']]]);
out.pick=_ensureModelOptionInDropdown('@custom:llama3.1:8b',sel,'custom');
out.pickLeft=sel.options.map(o=>o.value);
out.pickState=_modelStateForSelect(sel,sel.value);
return out;})()
