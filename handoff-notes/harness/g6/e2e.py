import json, sys, io, contextlib, subprocess
sys.path.insert(0, '.')
from api import config as c
sys.path.insert(0, 'tests')
import test_issue7955_route_js as t
BASE = "http://127.0.0.1:9/v1"
c._is_plugin_model_provider = lambda _: False
MODELS = ["qwen3:8b", "llama3.1:8b", "qwen2.5-coder:7b", "gemma2:9b"]
cfgd = {"model": {"provider": "lmstudio", "base_url": BASE, "default": "x"},
        "custom_providers": [{"base_url": BASE, "models": MODELS}]}
c.cfg.clear(); c.cfg.update(json.loads(json.dumps(cfgd)))
with contextlib.redirect_stderr(io.StringIO()):
    cat = c._static_models_catalog_without_live_probes()
groups = [{"provider_id": g.get("provider_id"), "ids": [m["id"] for m in g.get("models", [])]} for g in cat["groups"]]
print("CATALOG", groups)
js = r"""(()=>{
const sel=new Element('select');
for(const g of input.groups){const og=sel.appendChild(new Element('optgroup'));og.dataset.provider=g.provider_id;
  for(const id of g.ids){const o=og.appendChild(new Element('option'));o.value=id;}}
const removed=_deduplicateModelPickerOptions(sel,'');
const rows=sel.options.map(o=>({value:o.value,state:_modelStateForSelect(sel,o.value)}));
// restore each state
const restore=rows.map(r=>{const s2=new Element('select');
  for(const g of input.groups){const og=s2.appendChild(new Element('optgroup'));og.dataset.provider=g.provider_id;
    for(const id of g.ids){const o=og.appendChild(new Element('option'));o.value=id;}}
  return _findModelInDropdown(r.state.model,s2,r.state.model_provider);});
return {removed,rows,restore};})()"""
root = sys.argv[1]
d = t.DRIVER.replace("console.log(JSON.stringify(result));",
    "if(input.action==='custom'){result=eval(input.code);}\nconsole.log(JSON.stringify(result));")
d = d.replace("  eval(extract(ui,name));", "  const src=extract(ui,name); if(src) eval(src); else eval('var '+name+'=undefined');")
open('/opt/data/cache/scratch/g6/drv3.js', 'w').write(d)
p = subprocess.run(['node', '/opt/data/cache/scratch/g6/drv3.js', root,
                    json.dumps({'action': 'custom', 'code': js, 'groups': groups})], capture_output=True, text=True)
if p.returncode: print(p.stderr); sys.exit(1)
out = json.loads(p.stdout)
print("dedupe removed:", out["removed"])
for row, rest in zip(out["rows"], out["restore"]):
    st = row["state"]
    if not str(st["model_provider"] or "").startswith("custom"):
        continue
    wire = c.model_with_provider_context(st["model"], st["model_provider"])
    try:
        res = c.resolve_model_provider(wire)
    except Exception as e:
        res = f"ERR {e}"
    print(f"option {row['value']!r:28} state={st} wire={wire!r} resolved={res} restore_lookup={rest!r}")
