# Kera (GPT-6 Astra). Created 2026-09-19.
"""Full save/restart/restore test; only a disposable tmux server is touched."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time

parser = argparse.ArgumentParser()
parser.add_argument('--ktab', type=Path, default=Path(__file__).resolve().parents[2] / 'ktab')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
binary = str(args.ktab / 'bin/ktab')
tmp = tempfile.TemporaryDirectory(prefix='ktab-restore-', dir='/tmp')
socket = str(Path(tmp.name) / 'socket')
savedir = Path(tmp.name) / 'snapshots'
env = os.environ.copy()
env['TERM'] = 'xterm-256color'
env.pop('TMUX', None)
env.pop('TMUX_PANE', None)
child = None
master = None

def run(command, check=True):
    p = subprocess.run(command, env=env, text=True, capture_output=True, timeout=45)
    if check and p.returncode:
        raise AssertionError(f'{command}: {p.stdout} {p.stderr}')
    return p

def tm(*arguments):
    return run(['tmux', '-S', socket, *arguments]).stdout.rstrip('\n')

def kt(*arguments):
    return run([binary, *arguments]).stdout.rstrip('\n')

def drain(duration=.2):
    if master is None:
        return
    end = time.monotonic() + duration
    while time.monotonic() < end:
        ready, _, _ = select.select([master], [], [], max(0, end-time.monotonic()))
        if ready:
            try:
                os.read(master, 65536)
            except OSError:
                return

def wait_for(test, timeout=8):
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        if test():
            return
        drain(.1)
    raise AssertionError('tmux state did not converge')

def panes():
    return [line.split('\t') for line in tm('list-panes', '-a', '-F', '#{session_name}\t#{window_index}\t#{pane_id}\t#{pane_index}\t#{pane_pid}\t#{pane_current_command}\t#{@ktab_sidebar}').splitlines()]

def sidebar_count():
    return sum(p[-1] == '1' for p in panes())

def windows():
    return tm('list-windows', '-a', '-F', '#{session_name}|#{window_index}|#{window_name}|#{@ktab_group}')

def content_pids():
    return {p[4] for p in panes() if p[-1] != '1'}

def start(with_ktab=True):
    global child, master
    env.pop('TMUX', None)
    tm('-f', '/dev/null', 'new-session', '-d', '-s', '0', '-x', '110', '-y', '32', '/bin/sh')
    pid = tm('display-message', '-p', '#{pid}')
    tm('set-option', '-g', 'default-shell', '/bin/sh')
    tm('set-option', '-g', 'default-command', 'exec /bin/sh')
    tm('set-option', '-g', 'automatic-rename', 'off')
    tm('set-option', '-g', '@resurrect-dir', str(savedir))
    tm('set-option', '-g', '@resurrect-processes', 'false')
    child, master = pty.fork()
    if child == 0:
        os.execvpe('tmux', ['tmux', '-S', socket, 'attach-session', '-t', '0'], env)
    env['TMUX'] = f'{socket},{pid},0'
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 32, 110, 0, 0))
    drain()
    if with_ktab:
        run(['bash', str(args.ktab / 'ktab.tmux')])
        wait_for(lambda: sidebar_count() == 1)

def shutdown():
    global child, master
    run(['tmux', '-S', socket, 'kill-server'], check=False)
    if child:
        # Drain the PTY while the client exits; its final redraw can fill it.
        for _ in range(20):
            drain(.1)
            if os.waitpid(child, os.WNOHANG)[0]:
                break
        else:
            os.kill(child, signal.SIGKILL)
            os.waitpid(child, 0)
        child = None
    if master is not None:
        os.close(master)
        master = None

def save():
    run(['bash', str(root / 'scripts/save.sh'), 'quiet'])
    return (savedir / 'last').read_text()

def restore(check=True):
    p = run(['bash', str(root / 'scripts/restore.sh')], check=check)
    drain()
    return p

try:
    start()
    tm('rename-window', '-t', '0:0', 'book-process')
    tm('split-window', '-d', '-t', '0:0.0', '/bin/sh')
    tm('new-window', '-d', '-t', '0:2', '-n', 'book-browse', 'exec sleep 600')
    tm('new-window', '-d', '-t', '0:7', '-n', 'research', '/bin/sh')
    tm('new-session', '-d', '-s', 'notes session', '/bin/sh')
    tm('rename-window', '-t', 'notes session:0', 'notes')
    literal = "Books' \" ; $HOME #{window_name} \\"
    kt('group', 'set', '0:0', literal)
    kt('group', 'set', '0:2', literal)
    kt('group', 'set', '0:7', 'Research')
    kt('group', 'set', 'notes session:0', 'Writing')
    kt('group', 'collapse-all', '0:0')
    drain()
    expected = windows()
    expected_content_count = len(content_pids())
    snapshot = save()
    records = [line for line in snapshot.splitlines() if line.startswith('ktab\t')]
    assert len(records) == 1
    state = json.loads(records[0].split('\t', 1)[1])
    assert state['version'] == 1
    assert state['sessions'][0]['collapsed'] == [literal, 'Research']
    assert sum(line.startswith('ktab-pane\t') for line in snapshot.splitlines()) == 1
    assert len(state['windows']) == 4
    print('PASS: group membership, collapse state, literal names, disabled sidebar and pane marker saved', flush=True)

    shutdown()
    start()
    # A new tmux server assigns different IDs; restored identity is name/index.
    tm('new-window', '-d', '-n', 'temporary', '/bin/sh')
    tm('kill-window', '-t', '0:1')
    assert len(panes()) == 2, 'fresh bootstrap should contain a shell and ktab'
    restore()
    wait_for(lambda: windows() == expected)
    wait_for(lambda: sidebar_count() == 1)
    assert len(content_pids()) == expected_content_count, panes()
    assert tm('show-option', '-gqv', '@ktab_restoring') == ''
    sidebar = next(p[2] for p in panes() if p[-1] == '1')
    wait_for(lambda: tm('display-message', '-p', '-t', sidebar, '#{pane_current_command}') == 'ktab')
    capture = tm('capture-pane', '-p', '-t', sidebar)
    assert '▸ Books' in capture and '▸ Research' in capture, capture
    assert all(p[5] in ('sh', 'bash', 'ktab') for p in panes()), panes()
    assert tm('show-option', '-qv', '-t', 'notes session', '@ktab_enabled') == 'off'
    print('PASS: full server restart restores groups, collapsed active group, content panes and one working sidebar', flush=True)

    # A restore into an already populated server must preserve ordinary panes.
    tm('select-window', '-t', '0:7')
    wait_for(lambda: tm('display-message', '-p', '-t', sidebar, '#{window_index}') == '7')
    tm('split-window', '-d', '-t', '0:0.0', '/bin/sh')
    pids = content_pids()
    restore()
    wait_for(lambda: sidebar_count() == 1)
    assert pids <= content_pids(), 'restore respawned an existing content pane'
    assert windows() == expected
    print('PASS: repeated restore preserves running content panes and avoids duplicate sidebars', flush=True)

    # Invalid metadata must fail before resurrect touches ordinary panes.
    original_link = os.readlink(savedir / 'last')
    invalid = savedir / 'invalid.txt'
    invalid.write_text(snapshot.replace('"version":1', '"version":99'))
    (savedir / 'last').unlink()
    (savedir / 'last').symlink_to(invalid.name)
    pids = content_pids()
    assert restore(check=False).returncode != 0
    assert pids == content_pids()
    assert tm('show-option', '-gqv', '@ktab_restoring') == ''
    (savedir / 'last').unlink()
    (savedir / 'last').symlink_to(original_link)
    print('PASS: invalid version leaves content panes intact and releases restore guard', flush=True)

    # Ordinary snapshots still work with neither ktab installed nor metadata.
    kt('stop')
    tm('set-option', '-gqu', '@ktab_binary')
    time.sleep(1.1)  # resurrect filenames have one-second resolution
    legacy = save()
    assert not any(line.startswith('ktab') for line in legacy.splitlines())
    expected_names = [line.rsplit('|', 1)[0] for line in windows().splitlines()]
    shutdown()
    start(with_ktab=False)
    restore()
    assert [line.rsplit('|', 1)[0] for line in windows().splitlines()] == expected_names
    assert sidebar_count() == 0
    print('PASS: legacy save/restore remains usable without ktab', flush=True)
finally:
    shutdown()
    tmp.cleanup()
