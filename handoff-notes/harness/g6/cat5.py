import json, sys, io, contextlib
sys.path.insert(0, '.')
from api import config as c
BASE = "http://127.0.0.1:9/v1"
c._is_plugin_model_provider = lambda _: False
MODELS = ["qwen3:8b", "llama3.1:8b"]
configs = {}
for active in ["ollama", "lmstudio", "vllm", "local", "anthropic", "openrouter"]:
    configs[f"{active}+base+unnamed_cp"] = {"model": {"provider": active, "base_url": BASE, "default": "x"},
                                            "custom_providers": [{"base_url": BASE, "models": MODELS}]}
    configs[f"{active}+nobase+unnamed_cp"] = {"model": {"provider": active, "default": "x"},
                                              "custom_providers": [{"base_url": BASE, "models": MODELS}]}
    configs[f"{active}+base+model_list"] = {"model": {"provider": active, "base_url": BASE, "default": "qwen3:8b", "models": MODELS}}
for name, cfg in configs.items():
    c.cfg.clear(); c.cfg.update(json.loads(json.dumps(cfg)))
    with contextlib.redirect_stderr(io.StringIO()):
        out = c._static_models_catalog_without_live_probes()
    for g in out.get("groups", []):
        pid = g.get("provider_id", "")
        ids = [m.get("id") for m in (g.get("models", []) + (g.get("extra_models") or []))]
        hits = [i for i in ids if any(m in str(i) for m in MODELS)]
        if hits:
            print(name, "active=", out.get("active_provider"), "| group", pid, "|", hits)
