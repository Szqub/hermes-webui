(()=>{
const out={};
const sel=new Element('select');
const og=sel.appendChild(new Element('optgroup'));og.dataset.provider='custom';
const o=og.appendChild(new Element('option'));o.value='@custom:qwen3:8b';
sel.value='@custom:qwen3:8b';
// rich-dropdown pick of an overflow (extra_models) Custom entry: selectModelFromDropdown(value, providerId)
out.applied=_ensureModelOptionInDropdown('@custom:llama3.1:8b',sel,'custom');
out.selected=sel.value;
out.state=_modelStateForSelect(sel,sel.value);
out.opts=sel.options.map(x=>[x.value,x.dataset.provider||'(group)']);
return out;})()
