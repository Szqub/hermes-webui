import json, sys, copy
sys.path.insert(0, '.')
from api import config as C
C._is_plugin_model_provider = lambda _: False
BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
out = {"alias": {p: C._resolve_provider_alias(p) for p in ["ollama", "vllm", "lmstudio", "lm-studio", "llamacpp", "llama-cpp", "local", "custom"]}}
def safe(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)
CASES = {}
for act in ["lmstudio", "vllm", "llamacpp", "ollama", "local"]:
    CASES[act + " providers.custom@OTHER"] = {"model": {"provider": act, "base_url": BASE, "default": "llama3"},
        "providers": {"custom": {"base_url": OTHER, "models": ["mistral", "qwen3:8b"]}}}
    CASES[act + " cp unnamed@OTHER"] = {"model": {"provider": act, "base_url": BASE, "default": "llama3"},
        "custom_providers": [{"base_url": OTHER, "models": ["mistral", "qwen3:8b"]}]}
# dedup collision: Custom group + a provider sorted before 'custom' with same id
CASES["dedup ollama + anthropic same id"] = {"model": {"provider": "ollama", "base_url": BASE, "default": "claude-x"},
    "providers": {"anthropic": {"api_key": "sk-syn", "models": ["claude-x", "qwen3:8b"]}},
    "custom_providers": [{"base_url": OTHER, "models": ["qwen3:8b"]}]}
for name, conf in CASES.items():
    C.cfg = copy.deepcopy(conf)
    res = {"reserved": safe(getattr(C, "_configured_custom_lane_is_reserved", lambda: None))}
    cat = safe(C._static_models_catalog_without_live_probes)
    groups = cat.get("groups", []) if isinstance(cat, dict) else []
    res["active"] = cat.get("active_provider") if isinstance(cat, dict) else cat
    res["groups"] = {g.get("provider_id"): [m["id"] for m in g.get("models", [])] for g in groups}
    res["resolve"] = {}
    for g in groups:
        for m in g.get("models", []):
            if g.get("provider_id") in ("custom", "anthropic"):
                res["resolve"][g.get("provider_id") + "|" + m["id"]] = safe(C.resolve_model_provider, m["id"])
    for w in ["@custom:mistral", "@!:mistral", "mistral"]:
        res["resolve"]["raw|" + w] = safe(C.resolve_model_provider, w)
    out[name] = res
print(json.dumps(out, indent=1, default=str))
