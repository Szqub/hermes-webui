(()=>{
const out={};
for(const setVal of [false,true]){
const sel=new Element('select');
const og=sel.appendChild(new Element('optgroup'));og.dataset.provider='custom';
const o=og.appendChild(new Element('option'));o.value='@custom:qwen3:8b';
if(setVal) sel.value='@custom:qwen3:8b';
const value='@custom:qwen3:8b';
const selected=Array.from(sel.options).find(x=>String(x.value||'')===value);
const routedProvider=selected?String(_getOptionProviderId(selected)||'').trim():'';
out['rp'+setVal]=routedProvider;
out['dmodel'+setVal]=selected.dataset.model;
out['state'+setVal]=_modelStateForSelect(sel,value);
}
return out;})()
