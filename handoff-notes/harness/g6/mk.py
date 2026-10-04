import json, subprocess, sys
sys.path.insert(0, 'tests')
import test_issue7955_route_js as t
d = t.DRIVER.replace(
    "console.log(JSON.stringify(result));",
    "if(input.action==='custom'){result=eval(input.code);}\nconsole.log(JSON.stringify(result));")
open('/opt/data/cache/scratch/g6/drv.js', 'w').write(d)
code = open(sys.argv[1]).read()
p = subprocess.run(['node', '/opt/data/cache/scratch/g6/drv.js', '.', json.dumps({'action': 'custom', 'code': code})],
                   capture_output=True, text=True)
print(p.stderr)
for k, v in json.loads(p.stdout).items():
    print(k, '=>', json.dumps(v))
