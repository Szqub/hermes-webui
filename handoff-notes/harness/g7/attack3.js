(()=>{
function mk(groups){const sel=new Element('select');for(const [prov,vals] of groups){const g=sel.appendChild(new Element('optgroup'));g.dataset.provider=prov;for(const v of vals){const o=g.appendChild(new Element('option'));o.value=v;o.dataset.provider=prov;}}return sel;}
const out={};
const v='@custom:meta-llama/llama-3.3-70b-instruct:free';
let sel=mk([['custom',[v]],['alpha',['meta-llama/llama-3.3-70b-instruct:free']]]);
out.pickDedupCustomCopy=_modelStateForSelect(sel,v);
const v2='@custom:qwen3:8b';
sel=mk([['custom',[v2]],['alpha',['@alpha:qwen3:8b']]]);
out.pickCustomColon=_modelStateForSelect(sel,v2);
// restore that stored state
const st=out.pickDedupCustomCopy;
sel=mk([['custom',[v]],['alpha',['meta-llama/llama-3.3-70b-instruct:free']]]);
out.restore=_findModelInDropdown(st.model,sel,st.model_provider);
return out;})()
