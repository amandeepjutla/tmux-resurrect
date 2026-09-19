# Kera (GPT-6 Astra). Created 2026-09-19.
"""Exercise command notices on a disposable tmux server, including Fish."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[1]
fish = shutil.which('fish')
assert fish, 'Fish must be installed for this regression check'
tmp = tempfile.TemporaryDirectory(prefix='resurrect-notice-', dir='/tmp')
directory = Path(tmp.name)
socket = str(directory / 'socket')
savedir = directory / 'snapshots'
workdir = directory / "work's directory"
workdir.mkdir()
env = os.environ.copy()
env.pop('TMUX', None)
env.pop('TMUX_PANE', None)
env.update(TERM='xterm-256color', XDG_CONFIG_HOME=str(directory / 'config'),
           XDG_DATA_HOME=str(directory / 'data'))
conf = directory / 'config' / 'fish' / 'conf.d'
conf.mkdir(parents=True)
shutil.copyfile(root / 'shell/resurrect.fish', conf / 'tmux-resurrect.fish')


def run(argv, check=True):
    p = subprocess.run(argv, env=env, text=True, capture_output=True, timeout=30)
    if check and p.returncode:
        raise AssertionError(f'{argv}: {p.stdout} {p.stderr}')
    return p


def tm(*args):
    return run(['tmux', '-S', socket, *args]).stdout.rstrip('\n')


def start(shell=fish, default_command=''):
    env.pop('TMUX', None)
    tm('-f', '/dev/null', 'new-session', '-d', '-s', '0', '-x', '160', '-y', '45', '/bin/sh')
    env['TMUX'] = f"{socket},{tm('display-message', '-p', '#{pid}')},0"
    tm('set-option', '-g', 'default-shell', shell)
    tm('set-option', '-g', 'default-command', default_command)
    tm('set-option', '-g', 'automatic-rename', 'off')
    tm('set-option', '-g', '@resurrect-dir', str(savedir))
    tm('set-option', '-g', '@resurrect-processes', 'false')


def stop():
    run(['tmux', '-S', socket, 'kill-server'], check=False)


def wait_for(test):
    end = time.monotonic() + 8
    while time.monotonic() < end:
        if test():
            return
        time.sleep(.05)
    raise AssertionError('pane output did not converge')


def capture(target):
    return tm('capture-pane', '-p', '-J', '-S', '-', '-t', target)


def restore():
    run(['bash', str(root / 'scripts/restore.sh')])


try:
    start()
    tm('new-session', '-d', '-s', 'work', '-c', str(workdir))
    tm('split-window', '-d', '-t', 'work:0', '-c', str(workdir))
    tm('split-window', '-d', '-t', 'work:0', '-c', str(workdir))
    tm('new-window', '-d', '-t', 'work:2', '-c', str(workdir))
    tm('new-window', '-d', '-t', 'work:3', '-c', str(workdir))
    tm('new-session', '-d', '-s', 'other', '-c', str(workdir))
    tm('select-pane', '-t', 'work:0.2', '-T', 'sidebar')
    tm('set-option', '-p', '-t', 'work:0.2', '@ktab_sidebar', '1')
    completed = "printf 'finished\\n'"
    different = "printf 'a different completed command\\n'"
    tm('send-keys', '-t', 'work:3.0', completed, 'Enter')
    tm('send-keys', '-t', 'work:0.1', different, 'Enter')
    wait_for(lambda: tm('show-option', '-pqv', '-t', 'work:3.0', '@resurrect-last-command') == completed)
    wait_for(lambda: tm('show-option', '-pqv', '-t', 'work:0.1', '@resurrect-last-command') == different)
    wait_for(lambda: 'finished' in capture('work:3.0'))
    tm('send-keys', '-t', 'work:0.0', 'sleep 600', 'Enter')
    wait_for(lambda: tm('display-message', '-p', '-t', 'work:0.0', '#{pane_current_command}') == 'sleep')
    run(['bash', str(root / 'scripts/save.sh'), 'quiet'])
    records = (savedir / 'last').read_text().splitlines()
    running = next(line.split('\t') for line in records if line.startswith('pane\twork\t0\t') and line.split('\t')[5] == '0')
    assert running[10] == ':sleep 600', running
    assert 'command\twork\t3\t0\t:' + completed in records
    assert 'command\twork\t0\t1\t:' + different in records
    print('PASS: Fish tracks running and completed commands separately in each pane', flush=True)

    marker = directory / 'must-not-run'
    literal = f'''printf '%s\\n' "O'Reilly" $(touch {marker}) `touch {marker}` ; $HOME #{{pane_id}} café'''
    expected = {'work:0.0': 'sleep 600', 'work:0.1': literal,
                'work:3.0': completed, 'other:0.0': 'ssh example.test'}
    fixture = []
    for line in records:
        fields = line.split('\t')
        if fields[0] in ('pane', 'window') and fields[1] == '0':
            continue
        if fields[0] == 'pane':
            target = f'{fields[1]}:{fields[2]}.{fields[5]}'
            fields[10] = ':' + expected.get(target, 'sidebar-process' if target == 'work:0.2' else '')
            if target in ('work:0.1', 'work:3.0'):
                fields[10] = ':'  # Completed commands have no running process.
        elif fields[0] == 'command' and fields[1:4] == ['work', '0', '1']:
            fields[4] = ':' + literal
        fixture.append('\t'.join(fields))
    (savedir / 'fixture.txt').write_text('\n'.join(fixture) + '\n')
    (savedir / 'last').unlink()
    (savedir / 'last').symlink_to('fixture.txt')

    stop()
    start()
    # Exercise the special replacement of the sole bootstrap pane as well.
    tm('rename-session', '-t', '0', 'work')
    restore()
    for target, command in expected.items():
        wait_for(lambda: '[resurrect] Last command: ' + command in capture(target))
        actual_dir = tm('display-message', '-p', '-t', target, '#{pane_current_path}')
        assert Path(actual_dir).resolve() == workdir.resolve(), actual_dir
    assert not marker.exists(), 'saved command text was executed'
    assert '[resurrect]' not in capture('work:2.0')
    assert '[resurrect]' not in capture('work:0.2')
    assert tm('display-message', '-p', '-t', 'work:0.0', '#{pane_current_command}') == 'fish'
    print('PASS: saved running command, new sessions/windows/splits, literal text, Fish login shell, cwd and exclusions', flush=True)
    print(capture('work:0.0').strip(), flush=True)

    pids = tm('list-panes', '-a', '-F', '#{pane_pid}')
    before = {target: capture(target) for target in expected}
    restore()
    assert tm('list-panes', '-a', '-F', '#{pane_pid}') == pids
    assert {target: capture(target) for target in expected} == before
    print('PASS: repeated restore preserves existing processes and output', flush=True)

    run(['bash', str(root / 'scripts/save.sh'), 'quiet'])
    resaved = (savedir / 'last').read_text().splitlines()
    assert 'command\twork\t3\t0\t:' + completed in resaved
    assert 'command\twork\t0\t1\t:' + literal in resaved
    (savedir / 'last').unlink()
    (savedir / 'last').symlink_to('fixture.txt')
    print('PASS: remembered commands survive restoring and saving again', flush=True)

    stop()
    start('/bin/bash', "printf 'CUSTOM-STARTUP\\n'; exec /bin/bash --noprofile --norc")
    tm('set-option', '-g', '@resurrect-capture-pane-contents', 'on')
    contents = savedir / 'restore' / 'pane_contents'
    contents.mkdir(parents=True)
    (contents / 'pane-work:0.0').write_text('PREVIOUS-OUTPUT\n')
    restore()
    wait_for(lambda: 'CUSTOM-STARTUP' in capture('work:0.0'))
    output = capture('work:0.0')
    assert output.index('PREVIOUS-OUTPUT') < output.index('[resurrect]') < output.index('CUSTOM-STARTUP'), output
    assert literal in capture('work:0.1')
    assert not marker.exists()
    print('PASS: Bash, custom default-command and captured contents coexist with notices', flush=True)

    stop()
    start()
    tm('set-option', '-g', '@resurrect-show-command', 'off')
    restore()
    assert all('[resurrect]' not in capture(target) for target in expected)
    print('PASS: notices can be disabled', flush=True)

    # The printer itself neutralizes escape, carriage return, tab and newline.
    p = run(['bash', str(root / 'scripts/restore_command_notice.sh'),
             'one\x1b[31m\rtwo\tthree\nfour', '/bin/sh', 'exit', ''])
    assert p.stdout == '[resurrect] Last command: one [31m two three four\n\n', p.stdout
    print('PASS: terminal control characters are flattened', flush=True)
finally:
    stop()
    tmp.cleanup()
