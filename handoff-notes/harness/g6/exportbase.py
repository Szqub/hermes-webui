import subprocess, tarfile, os, io
wt = '/opt/data/cache/scratch/wt-design-7955'
dst = '/opt/data/cache/scratch/g6/expbase'
os.makedirs(dst, exist_ok=True)
data = subprocess.run(['git', '-C', wt, 'archive', 'cdff0b8d'], capture_output=True, check=True).stdout
with tarfile.open(fileobj=io.BytesIO(data)) as tf:
    tf.extractall(dst, filter='data')
link = os.path.join(dst, '.venv')
if not os.path.lexists(link):
    os.symlink(os.path.join(wt, '.venv'), link)
for f, needle in [('static/ui.js', 'laneId'), ('api/config.py', '_encode_catalog_route')]:
    print(f, needle, open(os.path.join(dst, f)).read().count(needle))
print(subprocess.run(['git', '-C', wt, 'rev-parse', 'cdff0b8d^{tree}'], capture_output=True, text=True).stdout)
