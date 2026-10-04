import json, sys, io, contextlib
sys.path.insert(0, '.')
from api import config as c
BASE = "http://127.0.0.1:9/v1"
c._is_plugin_model_provider = lambda _: False
MODELS = ["qwen3:8b", "llama3.1:8b"]
configs = {
  "anthropic+unnamed": {"model": {"provider": "anthropic", "default": "claude-sonnet-4-5"},
                        "custom_providers": [{"base_url": BASE, "models": MODELS}]},
  "anthropic+unnamed_model": {"model": {"provider": "anthropic", "default": "claude-sonnet-4-5"},
                        "custom_providers": [{"base_url": BASE, "model": "qwen3:8b"}]},
  "openrouter+unnamed": {"model": {"provider": "openrouter", "default": "x"},
                        "custom_providers": [{"base_url": BASE, "models": MODELS}]},
  "ollama_nobase+unnamed": {"model": {"provider": "ollama", "default": "llama3"},
                        "custom_providers": [{"base_url": BASE, "models": MODELS}]},
  "lmstudio+unnamed": {"model": {"provider": "lmstudio", "base_url": BASE, "default": "x"},
                        "custom_providers": [{"base_url": BASE, "models": MODELS}]},
}
for name, cfg in configs.items():
    c.cfg.clear(); c.cfg.update(json.loads(json.dumps(cfg)))
    with contextlib.redirect_stderr(io.StringIO()):
        out = c.get_available_models(force_refresh=True)
    print(name, "active=", out.get("active_provider"))
    for g in out.get("groups", []):
        pid = g.get("provider_id", "")
        ids = [m.get("id") for m in (g.get("models", []) + (g.get("extra_models") or []))]
        print("   group", pid, "|", ids[:6])
