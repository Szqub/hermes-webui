import os, shutil, subprocess, sys
SRC = '/opt/data/cache/scratch/g6/exp'
MUT = '/opt/data/cache/scratch/g6/mut'
env = dict(os.environ, HERMES_HOME='/opt/data/cache/scratch/design-7955-home',
           HERMES_WEBUI_STATE_DIR='/opt/data/cache/scratch/design-7955-state',
           HERMES_WEBUI_AGENT_DIR='/opt/data/cache/scratch/hermes-agent', TMPDIR='/tmp')
TESTS = ['tests/test_issue7955_disjoint_route.py', 'tests/test_issue7955_route_js.py',
         'tests/test_issue7290_no_slash_prefixed_alias.py', 'tests/test_model_picker_badges.py']
M = {
 'change1_hint_first': ('static/ui.js', "const preferred=String(explicitProvider||preferredProviderId||'').toLowerCase();",
                        "const preferred=String(preferredProviderId||explicitProvider||'').toLowerCase();"),
 'change2_no_laneId': ('static/ui.js', "return {model:routedModel||laneId||(isCustomProvider", "return {model:routedModel||(isCustomProvider"),
 'get_provider_cfg_canonical': ('api/config.py', "    if provider_cfg is None:\n        canonical = _canonicalise_provider_id(provider_id)",
                                "    if False:\n        canonical = _canonicalise_provider_id(provider_id)"),
 'routes_owns_exact_parsed': ('api/routes.py', "            if parsed and parsed[1].lower() == provider_id.lower():\n                candidate = parsed[0]\n            elif",
                              "            if False:\n                candidate = parsed[0]\n            elif"),
 'routes_compat_reserved_early': ('api/routes.py', "    if model.startswith(\"@!:\"):\n        return model, \"custom\", False\n",  ""),
 'reasoning_strip_new': ('api/config.py', "    if model.startswith(\"@!:\") or (model.startswith(\"@\") and \"%\" in model.split(\":\", 1)[0]):",
                         "    if False:"),
 'aux_parsed': ('api/config.py', "    if parsed and provider_id != \"auto\" and parsed[1] == provider_id.lower() and parsed[0]:",
                "    if False:"),
 'mwpc_reserved': ('api/config.py', "        return f\"@!:{model}\"\n\n    # ACP", "        pass\n\n    # ACP"),
 'resolver_reserved_failclosed': ('api/config.py', "        if not bare or not base or active.startswith(\"custom:\"):\n            raise ValueError",
                                  "        if False:\n            raise ValueError"),
 'render_display_regex': ('static/ui.js', "const displayName=/^@(?:!:|custom(?::|%3a))/i.test(rawValue)", "const displayName=rawValue.startsWith('@custom:')"),
 'normalize_key_reserved': ('static/ui.js', "if(typeof _parseModelRoute==='function'&&(s.startsWith('@!:')||/^@[^:]*%[^:]*:/.test(s))){", "if(false){"),
 'ensure_legacy_verbatim': ('static/ui.js', "  const legacyRecordRoute=(/^@custom:/i.test(rawModel)", "  const legacyRecordRoute=(false&&/^@custom:/i.test(rawModel)"),
 'label_reserved': ('static/ui.js', "  if(rawId.startsWith('@!:')) return rawId.slice(3)||rawId;\n", ""),
}
only = sys.argv[1:] or list(M)
for name in only:
    f, old, new = M[name]
    if os.path.exists(MUT):
        shutil.rmtree(MUT)
    shutil.copytree(SRC, MUT, symlinks=True)
    p = os.path.join(MUT, f)
    s = open(p).read()
    n = s.count(old)
    if n != 1:
        print(f'{name}: PATTERN COUNT {n} -- skipped'); continue
    open(p, 'w').write(s.replace(old, new))
    r = subprocess.run(['./scripts/test.sh', *TESTS, '-q', '--timeout=180', '-p', 'no:cacheprovider'],
                       cwd=MUT, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if ' passed' in l or ' failed' in l or 'error' in l.lower()][-1:]
    print(f'{name}: rc={r.returncode} {tail}')
