#!/usr/bin/env python3
"""One command to the owner's browser on the box (owner-browser.sh control: Firefox under Marionette, 127.0.0.1:2828).

  tabs                      the open tabs (the current one marked *)
  use HANDLE                make that tab the current one
  text [n]                  the page's visible text (first n characters, default 6000)
  inv                       the page's controls, numbered (each gets the attribute data-mi="<number>")
  goto URL
  eval FILE.js [json]       run the file as a function body in the page (arguments[0] is the json value); its return
                            value is printed. A returned promise is waited for.
  click N                   click control N of the last inv
  fill N TEXT               type TEXT into control N (cleared first) the way a person does (key events)
  file N PATH               give the file input N a file from this box's disk
  shot OUT.png
  pic                       where the stream's picture is drawn in the page (x y width height, video size)
  act JSON                  real mouse and key events (a list of steps; see act() below), e.g.
                            '[["pclick",0.1,0.45],["wait",2],["key","Tab"],["key","Enter"]]'

A password is never read: inv and text leave out the value of every password field, and nothing here types one.
"""
import base64
import json
import sys

from marionette_driver.by import By
from marionette_driver.marionette import Marionette

INV = r"""
const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
const lab = e => (e.innerText || e.getAttribute('aria-label') || e.title || e.placeholder || e.name || e.id || '')
  .trim().replace(/\s+/g, ' ').slice(0, 90);
const out = [];
let i = 0;
// Numbers of an earlier listing stay on elements the page has since hidden: clear them, or a number names two things.
document.querySelectorAll('[data-mi]').forEach(e => e.removeAttribute('data-mi'));
const sel ='a[href], button, input, select, textarea, [role=button], [role=tab], [role=switch], [role=checkbox], ' +
  '[role=radio], [role=menuitem], [role=option], [role=combobox], [contenteditable=true], label';
for (const e of document.querySelectorAll(sel)) {
  const t = e.tagName.toLowerCase(); const ty = e.getAttribute('type') || e.getAttribute('role') || '';
  if (!vis(e) && !(t === 'input' && ty === 'file')) continue;
  let v = '';
  if (t === 'input' && ty !== 'password') v = (ty === 'checkbox' || ty === 'radio') ? String(e.checked) : e.value;
  if (t === 'select' || t === 'textarea') v = e.value;
  const st = e.getAttribute('aria-checked') || e.getAttribute('aria-selected') || e.getAttribute('aria-pressed') ||
    e.getAttribute('data-state') || '';
  if (st) v = v ? v + ' [' + st + ']' : '[' + st + ']';
  e.setAttribute('data-mi', String(i));
  out.push(i + ' ' + t + (ty ? '[' + ty + ']' : '') + ' "' + lab(e) + '"' + (v !== '' ? ' = ' + String(v).slice(0, 160) : '') +
    (e.disabled ? ' (disabled)' : ''));
  i++;
}
return out.join('\n');
"""


PIC = r"""
const vs = [...document.querySelectorAll('video')].filter(v => v.videoWidth > 0 && v.getBoundingClientRect().width > 0);
if (!vs.length) return null;
const v = vs[vs.length - 1], r = v.getBoundingClientRect(), ar = v.videoWidth / v.videoHeight;
let w = r.width, h = r.width / ar;
if (h > r.height) { h = r.height; w = h * ar; }
return [r.x + (r.width - w) / 2, r.y + (r.height - h) / 2, w, h, v.videoWidth, v.videoHeight];
"""

JSMOVE = r"""
const a = arguments[0], dx = a[0], dy = a[1], n = a[2], gap = a[3];
const el = document.pointerLockElement || document.activeElement || document.body;
return new Promise(res => {
  let i = 0;
  const t = setInterval(() => {
    const ev = new MouseEvent('mousemove', {bubbles: true, cancelable: true, view: window, movementX: dx, movementY: dy,
      clientX: Math.round(innerWidth / 2), clientY: Math.round(innerHeight / 2)});
    el.dispatchEvent(ev);
    if (++i >= n) { clearInterval(t); res(i); }
  }, gap);
});
"""

KEYS = {'Tab': '', 'Enter': '', 'Escape': '', 'Space': ' ', 'Left': '', 'Up': '',
        'Right': '', 'Down': '', 'Shift': '', 'Control': ''}


def picture_rect(m):
    """Where the stream's picture is drawn in the page: x, y, width, height (and the video's own size)."""
    return m.execute_script(PIC)


def act(m, steps):
    """Real mouse and key events, as a person at the page makes them (a list of steps, each a list):
       ["pclick", fx, fy]       click at a place on the picture (fractions 0..1 of the picture)
       ["pmove", fx, fy]        move there
       ["click"]                click where the mouse is
       ["down"] / ["up"]        the left button
       ["moveby", dx, dy, n, gap_ms]   n relative mouse moves of dx, dy pixels, gap_ms apart (real pointer moves)
       ["jsmove", dx, dy, n, gap_ms]   the same as events the page receives from a locked mouse (this turns a locked view)
       ["key", "Tab"|"Enter"|"p"|..., hold_ms]    a key down, held, up
       ["keydown", k] / ["keyup", k]
       ["wait", seconds]"""
    import time

    def pointer(acts):
        m._send_message('WebDriver:PerformActions', {'actions': [
            {'type': 'pointer', 'id': 'mouse', 'parameters': {'pointerType': 'mouse'}, 'actions': acts}]})

    def keys(acts):
        m._send_message('WebDriver:PerformActions', {'actions': [{'type': 'key', 'id': 'kb', 'actions': acts}]})

    def to_px(fx, fy):
        r = picture_rect(m)
        if not r:
            raise RuntimeError('no video on the page')
        return int(r[0] + fx * r[2]), int(r[1] + fy * r[3])

    def move(x, y):
        return {'type': 'pointerMove', 'x': int(x), 'y': int(y), 'origin': 'viewport', 'duration': 0}

    cur = [None, None]   # where the pointer is (page pixels): Marionette refuses a move that would leave the page

    for s in steps:
        k = s[0]
        if k == 'wait':
            time.sleep(float(s[1]))
        elif k in ('pclick', 'pmove'):
            x, y = to_px(s[1], s[2])
            cur[0], cur[1] = x, y
            acts = [move(x, y)]
            if k == 'pclick':
                acts += [{'type': 'pointerDown', 'button': 0}, {'type': 'pause', 'duration': 60}, {'type': 'pointerUp', 'button': 0}]
            pointer(acts)
        elif k == 'click':
            pointer([{'type': 'pointerDown', 'button': 0}, {'type': 'pause', 'duration': 60}, {'type': 'pointerUp', 'button': 0}])
        elif k == 'down':
            pointer([{'type': 'pointerDown', 'button': 0}])
        elif k == 'up':
            pointer([{'type': 'pointerUp', 'button': 0}])
        elif k == 'moveby':
            # n mouse moves of dx, dy pixels, gap_ms apart. A locked mouse turns without end; the page does not: when
            # the pointer would leave the middle of the picture it jumps back to the middle in one move of more than
            # 400 pixels, which the game drops as a pointer-lock spike (a real browser reports none of these).
            dx, dy, n, gap = s[1], s[2], int(s[3]) if len(s) > 3 else 1, float(s[4]) if len(s) > 4 else 16
            r = picture_rect(m)
            cx, cy = r[0] + r[2] / 2.0, r[1] + r[3] / 2.0
            if cur[0] is None:
                cur[0], cur[1] = cx, cy
                pointer([move(cx, cy)])
                time.sleep(0.05)
            for _ in range(n):
                nx, ny = cur[0] + dx, cur[1] + dy
                if abs(nx - cx) > 450 or abs(ny - cy) > 250:
                    pointer([move(cx, cy)])
                    cur[0], cur[1] = cx, cy
                    nx, ny = cx + dx, cy + dy
                    time.sleep(0.03)
                pointer([move(nx, ny)])
                cur[0], cur[1] = nx, ny
                time.sleep(gap / 1000.0)
        elif k == 'jsmove':
            # n mouse-move events that carry their movement (movementX/Y), dispatched in the page on the locked
            # element or the document: what the player's page receives from a locked mouse. (Marionette's own pointer
            # moves do not turn a locked view: the browser derives no movement from them.)
            dx, dy, n, gap = s[1], s[2], int(s[3]) if len(s) > 3 else 1, float(s[4]) if len(s) > 4 else 16
            m.execute_script(JSMOVE, script_args=[[dx, dy, n, gap]])
        elif k == 'key':
            v = KEYS.get(s[1], s[1])
            hold = float(s[2]) if len(s) > 2 else 80
            keys([{'type': 'keyDown', 'value': v}, {'type': 'pause', 'duration': int(hold)}, {'type': 'keyUp', 'value': v}])
        elif k == 'keydown':
            keys([{'type': 'keyDown', 'value': KEYS.get(s[1], s[1])}])
        elif k == 'keyup':
            keys([{'type': 'keyUp', 'value': KEYS.get(s[1], s[1])}])
        else:
            raise RuntimeError('unknown step ' + k)
    try:
        m._send_message('WebDriver:ReleaseActions', {})
    except Exception:
        pass


def main():
    a = sys.argv[1:]
    c = a[0] if a else 'tabs'
    m = Marionette(host='127.0.0.1', port=2828, socket_timeout=80)
    m.start_session()
    try:
        m.timeout.script = 70
        if c == 'tabs':
            cur = m.current_window_handle
            for h in m.window_handles:
                m.switch_to_window(h)
                print(('* ' if h == cur else '  ') + h, '|', m.title, '|', m.get_url())
            m.switch_to_window(cur)
        elif c == 'use':
            m.switch_to_window(a[1])
            print(m.title, '|', m.get_url())
        elif c == 'text':
            n = int(a[1]) if len(a) > 1 else 6000
            t = m.execute_script("return document.body ? document.body.innerText : ''")
            print(m.title, '|', m.get_url())
            print(t[:n])
        elif c == 'goto':
            m.navigate(a[1])
            print(m.title, '|', m.get_url())
        elif c == 'inv':
            print(m.title, '|', m.get_url())
            print(m.execute_script(INV))
        elif c == 'eval':
            src = open(a[1]).read()
            arg = json.loads(a[2]) if len(a) > 2 else None
            r = m.execute_script(src, script_args=[arg], new_sandbox=False)
            print(r if isinstance(r, str) else json.dumps(r, indent=1))
        elif c in ('click', 'fill', 'file'):
            es = m.find_elements(By.CSS_SELECTOR, '[data-mi="%s"]' % a[1])
            if len(es) != 1:
                print('refused: %d elements carry the number %s (list the page again with inv)' % (len(es), a[1]))
                sys.exit(4)
            e = es[0]
            if e.get_attribute('type') == 'password':
                print('refused: a password field')
                sys.exit(3)
            if c == 'click':
                m.execute_script("arguments[0].scrollIntoView({block: 'center'})", script_args=[e])
                e.click()
            elif c == 'fill':
                m.execute_script("arguments[0].scrollIntoView({block: 'center'})", script_args=[e])
                e.click()
                e.clear()
                e.send_keys(a[2])
            else:
                # A file input is usually hidden (display: none) behind a drop zone, and a hidden element takes no
                # keys: show it for the moment, give it the path, put its style back.
                m.execute_script(
                    "const f = arguments[0]; f.setAttribute('data-mi-style', f.getAttribute('style') || '');"
                    "f.style.setProperty('display', 'block', 'important'); f.style.opacity = '0.01';"
                    "f.style.position = 'fixed'; f.style.left = '0'; f.style.top = '0';"
                    "f.style.width = '8px'; f.style.height = '8px';", script_args=[e])
                try:
                    e.send_keys(a[2])
                finally:
                    try:   # the page may have replaced the input as soon as it took the file
                        m.execute_script(
                            "const f = arguments[0]; f.setAttribute('style', f.getAttribute('data-mi-style'));"
                            "f.removeAttribute('data-mi-style');", script_args=[e])
                    except Exception:
                        pass
            print('ok', c, a[1])
        elif c == 'pic':
            print(json.dumps(picture_rect(m)))
        elif c == 'act':
            act(m, json.loads(a[1]))
            print('ok act', len(json.loads(a[1])), 'steps')
        elif c == 'shot':
            open(a[1], 'wb').write(base64.b64decode(m.screenshot()))
            print('saved', a[1])
        else:
            print('unknown command', c)
            sys.exit(2)
    finally:
        try:
            m.delete_session()
        except Exception as e:  # the browser went away: nothing to end
            print('note: delete_session:', e, file=sys.stderr)


main()
