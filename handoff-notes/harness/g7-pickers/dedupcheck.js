const fs=require('fs');
const root=process.argv[2];
const ui=fs.readFileSync(root+'/static/ui.js','utf8');
function extract(source,name){
  const start=source.indexOf('function '+name+'(');
  if(start<0) return '';
  const next=/\n(?:async )?function \w+\(/g; next.lastIndex=start+1;
  const end=next.exec(source);
  const block=source.slice(start,end?end.index:source.length);
  return block.slice(0,block.lastIndexOf('\n}')+2);
}
const window={_configuredModelBadges:{},_activeProvider:''};
const S={session:null};
for(const n of ['_parseModelRoute','_getOptionProviderId','_providerFromModelValue','_modelPickerOptionIdentity','_deduplicateModelPickerOptions']) eval(extract(ui,n));
class El{constructor(t){this.tagName=t.toUpperCase();this.children=[];this.dataset={};this.value='';this.id='';this.label='';}
 appendChild(c){c.parentElement=this;this.children.push(c);return c;}
 querySelectorAll(t){return this.children.filter(c=>c.tagName===t.toUpperCase());}
 removeChild(c){this.children=this.children.filter(x=>x!==c);}
 get options(){return this.children.flatMap(c=>c.tagName==='OPTGROUP'?c.children:[c]);}}
const sel=new El('select');
const g=sel.appendChild(new El('optgroup')); g.dataset.provider='custom';
const models=['qwen3:8b','llama3.1:8b','qwen2.5-coder:7b','gemma2:9b'];
for(const m of models){const o=g.appendChild(new El('option'));o.value='@custom:'+m;o.dataset.provider='custom';}
const before=sel.options.map(o=>o.value);
const ids=before.map(v=>_modelPickerOptionIdentity(v,'custom'));
const removed=_deduplicateModelPickerOptions(sel,'');
console.log(JSON.stringify({before,ids,removed,after:sel.options.map(o=>o.value)}));
