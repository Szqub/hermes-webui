import json, sys
h = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
print('alias', h.get('alias'))
for k in h:
    if k == 'alias':
        continue
    print('==', k, 'reserved', h[k].get('reserved'), 'active', h[k].get('active'))
    print('  head groups', h[k]['groups'])
    if b[k]['groups'] != h[k]['groups']:
        print('  base groups', b[k]['groups'])
    bres = b[k]['resolve']
    for r, v in h[k]['resolve'].items():
        if r.startswith('raw|'):
            print('   ', r, '->', v)
            continue
        alt = r.replace('|@!:', '|@custom:')
        print('   ', r, '->', v, '| base:', bres.get(r, bres.get(alt, 'n/a')))
