import sys
sys.path.insert(0, '.')
from api import config as C
for pid, models in sorted(C._PROVIDER_MODELS.items()):
    ids = [m.get('id') if isinstance(m, dict) else m for m in models]
    hits = [i for i in ids if i and ':' in i]
    if hits:
        print(pid, '<custom' if pid < 'custom' else '>custom', hits[:6])
