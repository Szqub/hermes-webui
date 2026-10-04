import json, sys, os
sys.path.insert(0, '.')
from api import config as c
BASE = "http://127.0.0.1:9/v1"
c.cfg.clear()
c.cfg.update({
    "model": {"provider": "anthropic", "default": "claude-sonnet-4-5"},
    "custom_providers": [{"base_url": BASE, "models": ["qwen3:8b", "llama3.1:8b", "gemma2:9b"]}],
})
c._is_plugin_model_provider = lambda _: False
try:
    out = c.get_available_models(force_refresh=True)
except Exception as e:
    print("ERR get_available_models", type(e).__name__, e)
    out = None
if out:
    for g in out.get("groups", []):
        print(g.get("provider_id"), [m.get("id") for m in g.get("models", [])])
for mid in ["qwen3:8b", "llama3.1:8b", "a/b:c"]:
    wire = c.model_with_provider_context(mid, "custom")
    print(mid, "->", wire, "->", c.resolve_model_provider(wire))
# truncated variant the browser can now emit
for mid, prov in [("8b", "custom:llama3.1")]:
    try:
        wire = c.model_with_provider_context(mid, prov)
        print(mid, prov, "->", wire, "->", c.resolve_model_provider(wire))
    except Exception as e:
        print(mid, prov, "ERR", type(e).__name__, e)
