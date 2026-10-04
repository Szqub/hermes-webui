import json, sys, io, contextlib
sys.path.insert(0, '.')
from api import config as c
BASE = "http://127.0.0.1:9/v1"
OTHER = "http://127.0.0.1:8/v1"
c._is_plugin_model_provider = lambda _: False
MODELS = ["qwen3:8b", "llama3.1:8b"]
configs = {
  "ollama+providers.box": {"model": {"provider": "ollama", "base_url": BASE, "default": "qwen3:8b", "models": MODELS},
                           "providers": {"box": {"base_url": OTHER, "api_key": "sk-x", "models": MODELS}}},
  "ollama+cp_box": {"model": {"provider": "ollama", "base_url": BASE, "default": "qwen3:8b"},
                    "custom_providers": [{"base_url": BASE, "models": MODELS}, {"name": "box", "base_url": OTHER, "models": MODELS}]},
  "ollama+providers.lab": {"model": {"provider": "ollama", "base_url": BASE, "default": "qwen3:8b", "models": MODELS},
                           "providers": {"lab": {"base_url": OTHER, "api_key": "sk-x", "models": MODELS}}},
}
for name, cfg in configs.items():
    c.cfg.clear(); c.cfg.update(json.loads(json.dumps(cfg)))
    with contextlib.redirect_stderr(io.StringIO()):
        out = c.get_available_models(force_refresh=True)
    for g in out.get("groups", []):
        pid = g.get("provider_id", "")
        ids = [m.get("id") for m in (g.get("models", []) + (g.get("extra_models") or []))]
        print(name, "| group", pid, "|", ids[:8])
