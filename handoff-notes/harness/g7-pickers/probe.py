import ast,json,subprocess,sys,types
from pathlib import Path
ROOT=Path('/opt/data/cache/scratch/wt-design-7955')
sys.path.insert(0,str(ROOT))
from api import config,profiles
source=(ROOT/'tests/test_issue7955_route_js.py').read_text()
driver=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DRIVER' for t in n.targets))
driver=driver.replace("}else if(input.action==='parse'){", """}else if(input.action==='metadata'){
 result=input.cases.map(([value,provider,requested,hint])=>{
   const sel=select(value,provider);
   return {matched:_findModelInDropdown(requested,sel,hint),state:_modelStateForSelect(sel,value)};
 });
}else if(input.action==='dedup'){
 const sel=select('@!:8b','custom');
 const opt=sel.children[0].appendChild(new Element('option'));opt.value='@custom:qwen3:8b';opt.dataset.provider='custom';
 result={removed:_deduplicateModelPickerOptions(sel,''),values:sel.options.map(o=>o.value)};
}else if(input.action==='parse'){""")
path=Path('/opt/data/cache/scratch/g7-pickers/routes.js');path.write_text(driver)
def js(action,**kw):
 p=subprocess.run(['node',str(path),str(ROOT),json.dumps(dict(action=action,**kw))],capture_output=True,text=True,check=True)
 return json.loads(p.stdout)
def test_probe():
 config.cfg={'model':{'provider':'ollama','base_url':'http://configured:11434/v1'}}
 print('actual opaque alias qualified model:',json.dumps(js('aliases',targets=[{'route_provider':'model-alias-canonical','model':'@!:qwen3:8b'}])))
 print('alias qualified object:',json.dumps(js('aliases',targets=[{'route_provider':'custom','model':'@!:qwen3:8b'},{'route_provider':'custom:east:west','model':'@custom%3Aeast%3Awest:qwen3:8b'}])))
 print('profile conflicting hint:',profiles._split_webui_provider_model_value('@!:qwen3:8b','custom:backup'))
 profile_dir=Path('/opt/data/cache/scratch/g7-pickers/profile');profile_dir.mkdir(exist_ok=True)
 profiles._write_model_defaults_to_config(profile_dir,default_model='@!:qwen3:8b',model_provider='custom:backup')
 print('profile persisted config:',json.dumps((profile_dir/'config.yaml').read_text()))
 config.cfg['fallback_providers']=[{'provider':'custom','model':'qwen3:8b'}]
 groups=[{'provider_id':'custom:qwen3','models':[{'id':'@custom:qwen3:8b'}]}]
 print('reserved custom badge on named option:',json.dumps(config._configured_model_badges_from_static_catalog(groups,active_provider=None,default_model='')))
 config.cfg.pop('fallback_providers')
 print('legacy scalar alias absent configured option:',json.dumps(js('aliases',targets=['custom/qwen3:8b'])))
 print('python resolver alias fallback:',config.resolve_model_provider(js('aliases',targets=['custom/qwen3:8b'])[0]['value']))
 print('unicode port parser python:',config._parse_provider_qualified_model_id('@custom:localhost:１２３:qwen3:8b'))
 print('unicode port parser JS:',json.dumps(js('parse',cases=[['@custom:localhost:１２３:qwen3:8b']])))
 print('restore conflicting option metadata:',json.dumps(js('metadata',cases=[['@custom:qwen3:8b','custom','@!:8b','custom'],['@other:8b','custom','@!:8b','custom']])))
 print('dedup same group different wire providers:',json.dumps(js('dedup')))
 config.cfg={'model':{'provider':'custom','base_url':'http://configured:11434/v1'}}
 print('configured custom helper:',config._configured_custom_lane_is_reserved())
 print('configured custom catalog:',config._apply_provider_prefix([{'id':'qwen3:8b'}],'custom','ollama'))
 print('configured custom explicit resolve:',config.resolve_model_provider('@!:qwen3:8b'))
 config.cfg={'model':{'provider':'ollama','base_url':'http://configured:11434/v1'}}
 print('slash catalog:',config._apply_provider_prefix([{'id':'vendor/qwen3:8b'}],'custom','ollama'))
 print('active custom catalog:',config._apply_provider_prefix([{'id':'qwen3:8b'}],'custom','custom'))
 print('live configured custom:',json.dumps(js('live',cases=[['custom','qwen3:8b']])))
 # Isolated synthetic core seeding module, no real core/config changes.
 core=types.ModuleType('hermes_cli.models');core._PROVIDER_MODELS={'custom:lab':['old','new']}
 sys.modules['hermes_cli.models']=core
 config._PROVIDER_MODELS={'custom:lab':[{'id':'@custom:lab:old','label':'old'}]}
 config._seed_provider_models_from_core();config._seed_provider_models_from_core()
 print('seed twice named prefix:',json.dumps(config._PROVIDER_MODELS))
