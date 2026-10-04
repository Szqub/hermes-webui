
const fs=require('fs');
const root=process.argv[2];
const ui=fs.readFileSync(root+'/static/ui.js','utf8');
const commands=fs.readFileSync(root+'/static/commands.js','utf8');
const panels=fs.readFileSync(root+'/static/panels.js','utf8');
function extract(source,name){
  const start=source.indexOf('function '+name+'(');
  if(start<0) return '';
  const next=/\n(?:async )?function \w+\(/g;
  next.lastIndex=start+1;
  const end=next.exec(source);
  const block=source.slice(start,end?end.index:source.length);
  return block.slice(0,block.lastIndexOf('\n}')+2);
}
const window={_configuredModelBadges:{},_activeProvider:''};
const S={session:null};
const _dynamicModelLabels={};
const _liveModelFetchPending=new Set();
const $=()=>null;
const syncModelChip=()=>{};
const _fmtOllamaLabel=s=>s;
const _stripDottedModelPrefix=s=>s;
for(const name of ['_encodeModelRoute','_parseModelRoute','_getOptionProviderId',
  '_providerFromModelValue','_modelPickerOptionIdentity','_modelStateForSelect',
  '_deduplicateModelPickerOptions','_findModelInDropdown','_refreshOpenModelDropdown',
  '_applyModelToDropdown','_ensureModelOptionInDropdown','_addLiveModelsToSelect',
  '_normalizeConfiguredModelKey','_isEquivalentConfiguredModelEntry','getModelLabel']){
  eval(extract(ui,name));
}
eval(extract(commands,'_resolveModelAliasTarget'));
eval(extract(panels,'_modelBareNameForProvider'));
class Element {
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.value='';this.id='';this.label='';}
  appendChild(child){child.parentElement=this;this.children.push(child);return child;}
  removeChild(child){this.children=this.children.filter(c=>c!==child);}
  querySelectorAll(tag){return this.children.filter(c=>c.tagName===tag.toUpperCase());}
  get options(){return this.children.flatMap(c=>c.tagName==='OPTGROUP'?c.children:[c]);}
  get selectedOptions(){return this.options.filter(c=>c.value===this.value);}
}
const document={createElement:tag=>new Element(tag)};
function select(value,provider){
  const sel=new Element('select');
  const group=sel.appendChild(new Element('optgroup'));group.dataset.provider=provider;
  const opt=group.appendChild(new Element('option'));opt.value=value;opt.dataset.provider=provider;
  sel.value=value;return sel;
}
const input=JSON.parse(process.argv[3]);
let result;
if(input.action==='consumers'){
  result=input.cases.map(([route,provider,model])=>{
    const sel=select(route,provider);
    return {provider:_providerFromModelValue(route),optionProvider:_getOptionProviderId({value:route}),
      identity:_modelPickerOptionIdentity(route,provider),state:_modelStateForSelect(sel,route),
      bare:_modelBareNameForProvider(route,provider),label:getModelLabel(route),
      match:_findModelInDropdown(model,sel,provider),
      badgeEquivalent:_isEquivalentConfiguredModelEntry(route,{provider},[{value:model,providerId:provider}])};
  });
}else if(input.action==='encode'){
  result=input.cases.map(([provider,model])=>_encodeModelRoute(provider,model));
}else if(input.action==='aliases'){
  result=input.targets.map(target=>_resolveModelAliasTarget(input.options||[],input.providerMap||{},target));
}else if(input.action==='inject'){
  result=input.cases.map(([provider,model])=>{
    const sel=new Element('select');
    const value=_ensureModelOptionInDropdown(model,sel,provider);
    return {value,state:_modelStateForSelect(sel,value),label:getModelLabel(value)};
  });
}else if(input.action==='inject-existing'){
  result=input.cases.map(([provider,model,preexisting])=>{
    const sel=new Element('select');
    const group=sel.appendChild(new Element('optgroup'));
    group.dataset.provider=String(provider).split(':')[0];
    for(const value of (preexisting||[])){
      const opt=group.appendChild(new Element('option'));
      opt.value=value;opt.dataset.provider=String(provider).split(':')[0];
    }
    const applied=_ensureModelOptionInDropdown(model,sel,provider);
    return {applied,selected:sel.value,options:sel.options.map(o=>o.value),
      state:_modelStateForSelect(sel,sel.value)};
  });
}else if(input.action==='live'){
  result=input.cases.map(([provider,model])=>{
    window._activeProvider=provider;
    const sel=new Element('select');
    _addLiveModelsToSelect(provider,[{id:model}],sel);
    const value=sel.options[0].value;
    return {value,state:_modelStateForSelect(sel,value)};
  });
}else if(input.action==='parse'){
  result=input.cases.map(([route,provider])=>_parseModelRoute(route,provider));
}
if(input.action==='custom'){result=eval(input.code);}
console.log(JSON.stringify(result));
