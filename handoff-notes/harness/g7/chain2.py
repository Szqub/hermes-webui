import json, sys, copy
sys.path.insert(0, '.')
from api import config as C
C._is_plugin_model_provider = lambda _: False
OTHER = "http://gpu-box:8000/v1"
def safe(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)
CASES = {
 "openai + providers.custom@OTHER": {"model": {"provider": "openai", "default": "gpt-4o"},
        "providers": {"custom": {"base_url": OTHER, "models": ["qwen3:8b"]}}},
 "openai + cp unnamed@OTHER": {"model": {"provider": "openai", "default": "gpt-4o"},
        "custom_providers": [{"base_url": OTHER, "models": ["qwen3:8b"]}]},
}
out = {}
for name, conf in CASES.items():
    C.cfg = copy.deepcopy(conf)
    cat = safe(C._static_models_catalog_without_live_probes)
    groups = cat.get("groups", []) if isinstance(cat, dict) else []
    r = {"custom_group": [m["id"] for g in groups if g.get("provider_id") == "custom" for m in g.get("models", [])]}
    for state in [("qwen3:8b", "custom"), ("8b", "custom:qwen3")]:
        w = safe(C.model_with_provider_context, *state)
        r[str(state)] = [w, safe(C.resolve_model_provider, w)]
    out[name] = r
print(json.dumps(out, indent=1))
