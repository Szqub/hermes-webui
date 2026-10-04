import json, subprocess, sys
drv, root, code = sys.argv[1], sys.argv[2], open(sys.argv[3]).read()
p = subprocess.run(['node', drv, root, json.dumps({'action': 'custom', 'code': code})], capture_output=True, text=True)
if p.returncode:
    print(p.stderr[-3000:])
    sys.exit(1)
res = json.loads(p.stdout)
for k, v in res.items():
    if isinstance(v, dict) and k == 'ensureMatrix':
        for kk, vv in v.items():
            print('ensure', kk)
            for row in vv:
                print('    ', json.dumps(row))
    else:
        print(k, '=>', json.dumps(v))
