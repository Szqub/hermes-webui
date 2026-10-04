import json, sys, copy
sys.path.insert(0, '.')
from api import config as C
C._is_plugin_model_provider = lambda _: False
BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
def safe(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)
CASES = {
 "lmstudio+providers.custom@OTHER": {"model": {"provider": "lmstudio", "base_url": BASE, "default": "llama3"},
        "providers": {"custom": {"base_url": OTHER, "models": ["mistral"]}}},
 "llamacpp+providers.custom@OTHER": {"model": {"provider": "llamacpp", "base_url": BASE, "default": "llama3"},
        "providers": {"custom": {"base_url": OTHER, "models": ["mistral"]}}},
 "ollama+providers.custom@OTHER": {"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"},
        "providers": {"custom": {"base_url": OTHER, "models": ["mistral"]}}},
 "lmstudio+cp unnamed@OTHER": {"model": {"provider": "lmstudio", "base_url": BASE, "default": "llama3"},
        "custom_providers": [{"base_url": OTHER, "models": ["mistral"]}]},
}
out = {}
for name, conf in CASES.items():
    C.cfg = copy.deepcopy(conf)
    wire = safe(C.model_with_provider_context, "mistral", "custom")
    out[name] = {"session_wire(mistral,custom)": wire, "resolved": safe(C.resolve_model_provider, wire)}
print(json.dumps(out, indent=1))
