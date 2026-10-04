import os, re, subprocess, sys
env = dict(os.environ, HERMES_HOME='/opt/data/cache/scratch/design-7955-home',
           HERMES_WEBUI_STATE_DIR='/opt/data/cache/scratch/design-7955-state',
           HERMES_WEBUI_AGENT_DIR='/opt/data/cache/scratch/hermes-agent', TMPDIR='/tmp')
pat = re.compile(r"model|provider|custom|picker|alias|7955|6221|6884|6195|7240|1771", re.I)
for d in sys.argv[1:]:
    root = f'/opt/data/cache/scratch/g6/{d}'
    files = sorted('tests/' + f for f in os.listdir(root + '/tests') if pat.search(f) and f.endswith('.py'))
    r = subprocess.run(['./scripts/test.sh', *files, '-q', '--timeout=180', '-p', 'no:cacheprovider'],
                       cwd=root, env=env, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith(('FAILED', 'ERROR')) or ' passed' in l or ' failed' in l]
    print(f'== {d} rc={r.returncode} files={len(files)}')
    print('\n'.join(lines[-10:]))
