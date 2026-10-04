import json, sys, copy
sys.path.insert(0, '.')
from api import config as C
C._is_plugin_model_provider = lambda _: False
BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
M = "qwen3:8b"
CASES = {
 "A ollama+base, cp named 'custom'": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"name": "custom", "base_url": OTHER, "models": [M]}]},
 "B ollama+base, cp unnamed": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"base_url": OTHER, "models": [M]}]},
 "B2 ollama+base, cp unnamed same base": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"base_url": BASE, "models": [M]}]},
 "C ollama+base, providers.custom other": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
     "providers": {"custom": {"base_url": OTHER, "models": [M]}}},
 "D custom+base": {"model": {"provider": "custom", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"base_url": OTHER, "models": [M]}]},
 "E ollama no base, cp unnamed": {"model": {"provider": "ollama", "default": "llama3"},
     "custom_providers": [{"base_url": OTHER, "models": [M]}]},
 "F active custom:lab + base": {"model": {"provider": "custom:lab", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"name": "lab", "base_url": BASE, "models": ["x"]}, {"base_url": OTHER, "models": [M]}]},
 "G local+base, cp unnamed": {"model": {"provider": "local", "base_url": BASE, "default": "llama3"},
     "custom_providers": [{"base_url": OTHER, "models": [M]}]},
 "H openai+base, cp unnamed": {"model": {"provider": "openai", "base_url": BASE, "default": "gpt-4o"},
     "custom_providers": [{"base_url": OTHER, "models": [M]}]},
 "I ollama+base, providers.custom no base": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
     "providers": {"custom": {"models": [M]}}},
}
def safe(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)
out = {}
for name, conf in CASES.items():
    C.cfg = copy.deepcopy(conf)
    res = {}
    res["reserved"] = safe(getattr(C, "_configured_custom_lane_is_reserved", lambda: None))
    cat = safe(C._static_models_catalog_without_live_probes)
    groups = cat.get("groups", []) if isinstance(cat, dict) else cat
    res["groups"] = [(g.get("provider_id"), [m["id"] for m in g.get("models", [])]) for g in groups] if isinstance(groups, list) else groups
    res["resolve"] = {}
    if isinstance(groups, list):
        for g in groups:
            if g.get("provider_id") in ("custom",) or str(g.get("provider_id")).startswith("custom:"):
                for m in g.get("models", []):
                    res["resolve"][m["id"]] = safe(C.resolve_model_provider, m["id"])
    res["session_wire"] = safe(C.model_with_provider_context, M, "custom")
    res["resolve_session_wire"] = safe(C.resolve_model_provider, res["session_wire"]) if isinstance(res["session_wire"], str) else None
    out[name] = res
print(json.dumps(out, indent=1, default=str))
