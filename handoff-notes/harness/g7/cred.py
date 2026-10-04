import json, os, sys
sys.path.insert(0, '.')
home = os.environ['HERMES_HOME']
os.makedirs(home, exist_ok=True)
variant = sys.argv[1]
BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
cfgs = {
 'providers_custom': "model:\n  provider: lmstudio\n  base_url: %s\n  default: llama3\nproviders:\n  custom:\n    base_url: %s\n    api_key: sk-synthetic-OTHER-key\n    models: [mistral]\n" % (BASE, OTHER),
 'ollama_providers_custom': "model:\n  provider: ollama\n  base_url: %s\n  default: llama3\nproviders:\n  custom:\n    base_url: %s\n    api_key: sk-synthetic-OTHER-key\n    models: [mistral]\n" % (BASE, OTHER),
 'ollama_providers_ollama': "model:\n  provider: ollama\n  base_url: %s\n  default: llama3\nproviders:\n  ollama:\n    base_url: http://other:9999/v1\n    api_key: sk-synthetic-OTHER-key\n" % (BASE,),
 'local_providers_local': "model:\n  provider: local\n  base_url: %s\n  default: llama3\nproviders:\n  local:\n    base_url: http://other:9999/v1\n    api_key: sk-synthetic-OTHER-key\n" % (BASE,),
 'vllm_providers_custom_key_only': "model:\n  provider: vllm\n  base_url: %s\n  default: llama3\nproviders:\n  custom:\n    api_key: sk-synthetic-OTHER-key\n" % (BASE,),
 'cp_unnamed': "model:\n  provider: lmstudio\n  base_url: %s\n  default: llama3\ncustom_providers:\n  - base_url: %s\n    api_key: sk-synthetic-OTHER-key\n    models: [mistral]\n" % (BASE, OTHER),
}
open(os.path.join(home, 'config.yaml'), 'w').write(cfgs[variant])
from api import config as C
C.reload_config() if hasattr(C, 'reload_config') else None
C._is_plugin_model_provider = lambda _: False
out = {}
wire = C.model_with_provider_context('mistral', 'custom')
out['wire'] = wire
try:
    m, p, b = C.resolve_model_provider(wire)
    out['resolved'] = [m, p, b]
except Exception as e:
    out['resolved'] = repr(e); m = p = b = None
try:
    from hermes_cli.runtime_provider import resolve_runtime_provider
    rt = resolve_runtime_provider(requested=p, target_model=m)
    key = rt.get('api_key') or ''
    out['runtime'] = {'provider': rt.get('provider'), 'base_url': rt.get('base_url'),
                      'api_key_is_OTHER_key': key == 'sk-synthetic-OTHER-key', 'api_key_present': bool(key)}
except Exception as e:
    out['runtime'] = repr(e)
try:
    from api import streaming as S
    final_base = S._runtime_preferred_base_url(rt, p, b)
    out['final_base_url'] = final_base
    bundle = S._resolve_runtime_connection_bundle(p, rt.get('api_key'), final_base, rt, profile_name=None, custom_provider_lookup=p)
    out['bundle'] = {k: (v if k != 'api_key' else ('OTHER-KEY' if v == 'sk-synthetic-OTHER-key' else bool(v))) for k, v in bundle.items() if k in ('provider', 'base_url', 'api_key', 'api_mode')}
except Exception as e:
    out['bundle'] = repr(e)
print(json.dumps(out, indent=1, default=str))
