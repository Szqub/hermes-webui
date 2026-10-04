import os, subprocess, sys, shutil
WT = '/opt/data/cache/scratch/wt-design-7955'
BASE = '/opt/data/cache/scratch/g7/mut'
env = dict(os.environ, HERMES_HOME='/opt/data/cache/scratch/design-7955-home',
           HERMES_WEBUI_STATE_DIR='/opt/data/cache/scratch/design-7955-state',
           HERMES_WEBUI_AGENT_DIR='/opt/data/cache/scratch/hermes-agent', TMPDIR='/tmp')
MUTANTS = {
 'M1_ensure_wraps_qualified': ('static/ui.js',
   "  const qualifiedRoute=route;\n",
   "  const qualifiedRoute=(/^@custom:/i.test(rawModel)&&rawModel.slice('@custom:'.length).includes(':')&&route)?route:null;\n"),
 'M2_find_exact_ignores_provider': ('static/ui.js',
   "        return !p||p===requested;\n", "        return true;\n"),
 'M3_state_group_wins': ('static/ui.js',
   "        model_provider:valueProvider||effectiveProvider};",
   "        model_provider:effectiveProvider};"),
 'M3b_state_strip_any': ('static/ui.js',
   "      const stripToId=valueProvider==='custom'||valueProvider.startsWith('custom:');",
   "      const stripToId=true;"),
 'M4_catalog_generic': ('api/config.py',
   "    if _canonicalise_provider_id(provider_id) == \"custom\" and _configured_custom_lane_is_reserved():\n        return f\"@!:{model_id}\"\n",
   ""),
 'M5_reserved_ignores_named_active': ('api/config.py',
   "    if not base or active.startswith(\"custom:\"):\n        return False\n    return active == \"local\" or _is_local_server_provider(active)",
   "    if not base:\n        return False\n    return active == \"local\" or _is_local_server_provider(active)"),
 'M6_reserved_ignores_base': ('api/config.py',
   "    if not base or active.startswith(\"custom:\"):\n        return False\n    return active == \"local\" or _is_local_server_provider(active)",
   "    if active.startswith(\"custom:\"):\n        return False\n    return active == \"local\" or _is_local_server_provider(active)"),
 'M7_reserved_accepts_custom': ('api/config.py',
   "    return active == \"local\" or _is_local_server_provider(active)\n\n\ndef _encode_catalog_route",
   "    return active in (\"local\", \"custom\") or _is_local_server_provider(active)\n\n\ndef _encode_catalog_route"),
 'M8_dedup_generic': ('api/config.py',
   "            model[\"id\"] = _encode_catalog_route(original_id, pid)",
   "            model[\"id\"] = _encode_provider_qualified_model_id(original_id, pid)"),
 'M9_prefix_generic': ('api/config.py',
   "            entry[\"id\"] = _encode_catalog_route(mid, provider_id)",
   "            entry[\"id\"] = _encode_provider_qualified_model_id(mid, provider_id)"),
 'M10_seed_generic': ('api/config.py',
   "inject_id = _encode_catalog_route(mid.strip(), webui_key) if _prefix else mid.strip()",
   "inject_id = _encode_provider_qualified_model_id(mid.strip(), webui_key) if _prefix else mid.strip()"),
 'M11_default_backstop_generic': ('api/config.py',
   "_encode_catalog_route(default_model, active_provider) not in all_model_ids",
   "_encode_provider_qualified_model_id(default_model, active_provider) not in all_model_ids"),
}
only = sys.argv[1:]
for name, (path, old, new) in MUTANTS.items():
    if only and name not in only:
        continue
    d = os.path.join(BASE, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    subprocess.run(f'git -C {WT} archive HEAD | tar -x -C {d}', shell=True, check=True)
    os.symlink(WT + '/.venv', d + '/.venv')
    p = os.path.join(d, path)
    src = open(p).read()
    n = src.count(old)
    if n != 1:
        print(f'{name}: pattern count {n} -- SKIPPED')
        continue
    open(p, 'w').write(src.replace(old, new))
    r = subprocess.run(['./scripts/test.sh', 'tests/test_issue7955_disjoint_route.py', 'tests/test_issue7955_route_js.py',
                        '-q', '--timeout=180', '-p', 'no:cacheprovider'], cwd=d, env=env, capture_output=True, text=True)
    summ = [l for l in r.stdout.splitlines() if ' passed' in l or ' failed' in l]
    fails = [l for l in r.stdout.splitlines() if l.startswith('FAILED')]
    print(f'{name}: rc={r.returncode} {summ[-1] if summ else r.stdout[-300:]}')
    for f in fails[:6]:
        print('    ', f[:200])
