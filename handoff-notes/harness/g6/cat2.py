import json, sys, io, contextlib
sys.path.insert(0, '.')
from api import config as c
BASE = "http://127.0.0.1:9/v1"
c._is_plugin_model_provider = lambda _: False
MODELS = ["qwen3:8b", "llama3.1:8b"]
configs = {}
for active in ["ollama", "lmstudio", "vllm", "local", "openrouter", "anthropic", "openai", "deepseek"]:
    configs[f"{active}+unnamed_cp"] = {"model": {"provider": active, "base_url": BASE, "default": "x"},
                                       "custom_providers": [{"base_url": BASE, "models": MODELS}]}
    configs[f"{active}+named_cp"] = {"model": {"provider": active, "base_url": BASE, "default": "x"},
                                     "custom_providers": [{"name": "lab", "base_url": BASE, "models": MODELS}]}
    configs[f"{active}+model_list"] = {"model": {"provider": active, "base_url": BASE, "default": "qwen3:8b", "models": MODELS}}
for name, cfg in configs.items():
    c.cfg.clear(); c.cfg.update(json.loads(json.dumps(cfg)))
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            out = c.get_available_models(force_refresh=True)
    except Exception as e:
        print(name, "ERR", type(e).__name__, str(e)[:100]); continue
    for g in out.get("groups", []):
        pid = g.get("provider_id", "")
        ids = [m.get("id") for m in (g.get("models", []) + (g.get("extra_models") or []))]
        hits = [i for i in ids if any(m in str(i) for m in MODELS)]
        if hits:
            print(name, "| group", pid, "|", hits)
