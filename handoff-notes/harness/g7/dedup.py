import json, sys, copy
sys.path.insert(0, '.')
from api import config as C
C._is_plugin_model_provider = lambda _: False
BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
MID = "meta-llama/llama-3.3-70b-instruct:free"
def safe(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)
CASES = {
 "custom+base, providers.alpha same slash:colon id": {
    "model": {"provider": "custom", "base_url": BASE, "default": MID},
    "providers": {"alpha": {"base_url": OTHER, "api_key": "sk-synthetic", "models": [MID]}}},
 "ollama+base, providers.alpha same slash:colon id": {
    "model": {"provider": "ollama", "base_url": BASE, "default": MID},
    "providers": {"alpha": {"base_url": OTHER, "api_key": "sk-synthetic", "models": [MID]}}},
}
out = {}
for name, conf in CASES.items():
    C.cfg = copy.deepcopy(conf)
    cat = safe(C._static_models_catalog_without_live_probes)
    groups = cat.get("groups", []) if isinstance(cat, dict) else []
    r = {"reserved": safe(getattr(C, "_configured_custom_lane_is_reserved", lambda: None)),
         "active": cat.get("active_provider") if isinstance(cat, dict) else cat,
         "groups": {g.get("provider_id"): [m["id"] for m in g.get("models", [])] for g in groups}}
    for state in [(MID, "custom"), ("free", "custom:meta-llama/llama-3.3-70b-instruct")]:
        w = safe(C.model_with_provider_context, *state)
        r["state " + str(state)] = [w, safe(C.resolve_model_provider, w)]
    out[name] = r
print(json.dumps(out, indent=1))
