import importlib.util,subprocess
from pathlib import Path
ROOT=Path('/opt/data/cache/scratch/wt-design-7955')
spec=importlib.util.spec_from_file_location('route_tests',ROOT/'tests/test_issue7955_route_js.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=Path('/opt/data/cache/scratch/g7-pickers/mutations');base.mkdir(exist_ok=True)
def test_mutations():
 for kind in ('panels-parser-removed','commands-encoder-removed','live-encoder-removed'):
  overlay=base/kind;(overlay/'static').mkdir(parents=True,exist_ok=True)
  for name in ('ui.js','commands.js','panels.js'):
   text=(ROOT/'static'/name).read_text()
   if kind=='panels-parser-removed' and name=='panels.js':
    text=text.replace("  if(model&&provider&&typeof _parseModelRoute==='function'){\n    const route=_parseModelRoute(model,provider);\n    return route&&route.provider===String(provider).trim().toLowerCase()?route.model:model;\n  }\n",'')
   if kind=='commands-encoder-removed' and name=='commands.js':
    text=text.replace("const value=routeProvider==='custom'?`@!:${model}`\n        :typeof _encodeModelRoute==='function'?_encodeModelRoute(routeProvider,model):`@${routeProvider.replace(/%/g,'%25').replace(/!/g,'%21')}:${model}`;","const value=`@${routeProvider}:${model}`;")
   if kind=='live-encoder-removed' and name=='ui.js':
    text=text.replace("mid=typeof _encodeModelRoute==='function'?_encodeModelRoute(provider,mid):`@${provider.replace(/%/g,'%25').replace(/!/g,'%21')}:${mid}`;","mid=`@${provider}:${mid}`;")
   (overlay/'static'/name).write_text(text)
  m.ROOT=overlay
  failed=[];passed=[]
  for name in dir(m):
   if not name.startswith('test_') or name=='test_python_browser_encoder_parity':continue
   try:getattr(m,name)(base);passed.append(name)
   except AssertionError:failed.append(name)
  print(kind,'caught_by',failed,'passed',len(passed))
