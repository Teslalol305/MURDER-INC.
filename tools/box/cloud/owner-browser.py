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
                e.send_keys(a[2])
            print('ok', c, a[1])
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
