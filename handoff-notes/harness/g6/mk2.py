import json, subprocess, sys, os
sys.path.insert(0, 'tests')
import test_issue7955_route_js as t
root = sys.argv[2]
d = t.DRIVER.replace(
    "console.log(JSON.stringify(result));",
    "if(input.action==='custom'){result=eval(input.code);}\nconsole.log(JSON.stringify(result));")
# tolerate missing helpers at base
d = d.replace("  eval(extract(ui,name));", "  const src=extract(ui,name); if(src) eval(src); else eval('var '+name+'=undefined');")
open('/opt/data/cache/scratch/g6/drv2.js', 'w').write(d)
code = open(sys.argv[1]).read()
p = subprocess.run(['node', '/opt/data/cache/scratch/g6/drv2.js', root, json.dumps({'action': 'custom', 'code': code})],
                   capture_output=True, text=True)
print(p.stderr[-2000:])
for k, v in json.loads(p.stdout).items():
    print(k, '=>', json.dumps(v))
