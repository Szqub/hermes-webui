import os, subprocess, sys
root = sys.argv[1]
tests = sys.argv[2:]
env = dict(os.environ, HERMES_HOME='/opt/data/cache/scratch/design-7955-home',
           HERMES_WEBUI_STATE_DIR='/opt/data/cache/scratch/design-7955-state',
           HERMES_WEBUI_AGENT_DIR='/opt/data/cache/scratch/hermes-agent', TMPDIR='/tmp')
if not os.path.exists(root + '/.venv'):
    os.symlink('/opt/data/cache/scratch/wt-design-7955/.venv', root + '/.venv')
r = subprocess.run(['./scripts/test.sh', *tests, '-q', '--timeout=180', '-p', 'no:cacheprovider', '-rf'],
                   cwd=root, env=env, capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.startswith(('FAILED', 'ERROR', 'E  ')) or ' passed' in l or ' failed' in l]
print(f'== {root} rc={r.returncode}')
print('\n'.join(lines[-30:]))
