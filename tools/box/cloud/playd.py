# An interactive viewer: rtcinput.py's viewer, but it plays the lines that are appended to a command file while it runs
# instead of a script read at the start, so a tester can look at a frame, decide, and send the next input (the independent
# play of release v6). Same verbs as rtcinput.py (its header), plus "quit". Output (viewer log) goes to stdout.
#   python playd.py <streamerId> <command file> [rtcinput.py's options, e.g. --out DIR --player 1920x1080]
# Append a line:   echo "key 13" >> cmds.txt      A "frame name.jpg" line saves the next video frame into --out.
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'rtcinput.py')).read()
src = src.replace("lines = (sys.stdin if A.script == '-' else open(A.script)).read().splitlines()", "lines = []")
src = src.replace("        await play(lines, send, Player(w, h))\n", '''        player = Player(w, h)
        done = 0
        open(A.script, 'a').close()
        while True:
            new = open(A.script).read().splitlines()[done:]
            if not new:
                await asyncio.sleep(0.05)
                continue
            for ln in new:
                done += 1
                if ln.split('#', 1)[0].strip() == 'quit':
                    new = None
                    break
                await play([ln], send, player)
            if new is None:
                break
''')
assert 'quit' in src
sys.argv[0] = os.path.join(here, 'rtcinput.py')
exec(compile(src, sys.argv[0], 'exec'), {'__name__': '__main__', '__file__': sys.argv[0]})
