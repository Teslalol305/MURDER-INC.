# A WebRTC viewer without a browser that also plays: it subscribes to the game through Epic's signalling server
# (e3ds-repro.sh ss start: players on port 8090), answers the offer, receives the video, and sends mouse, keyboard,
# gamepad and command messages over the data channel exactly as Pixel Streaming's browser player does (the message ids
# and layouts of PixelStreaming2Input's default protocol, the mouse maths of the reference front end). The box cannot
# run a browser viewer (docs/unreal/BOX.md), so this is how input through the stream is tested there.
#
#   python rtcinput.py <streamerId> <script file or -> [--player WxH] [--out DIR] [--port 8090] [--nodecode]
#                      [--delay-ms N] [--link-kbps N] [--link-queue-ms N] [--remb-kbps N]
#
# The box has no tc/netem (a gVisor sandbox: no ip, no tc), so the link of a viewer is made in the viewer: --delay-ms adds
# that much round trip (half to every packet the viewer receives, half to every one it sends: the game's round trip, which
# it measures from the viewer's RTCP reports, grows by N ms); --link-kbps makes the viewer's downlink a bottleneck of
# that rate with a drop-tail queue of --link-queue-ms (default 150): packets that would wait longer are dropped, as at a
# router; --remb-kbps sets the bandwidth this viewer tells the sender it can take (the receiver-estimated bitrate it sends
# every second; aiortc's own estimate is low and unsteady, BOX.md), so that "a link of 4 Mbit/s" is also what the sender
# is told. With none of these the viewer is as it was.
#
# --nodecode leaves the video undecoded (the frames are only counted as they arrive; "frame" lines save nothing): a
# viewer that costs the machine almost no CPU, to see whether the decoding beside the game changes what the game's
# encoder manages.
#
# --player is the size the page would show the picture at, in browser pixels (default: the video's own size, which is
# what E3DS's Dynamic resolution gives); mouse movement is given in those pixels. Script lines (# starts a comment):
#   wait <seconds>
#   say <text>                          print a line with the time (to line up with the game's log)
#   click [x y]                         left button down and up at a place (fractions 0..1 of the picture; default 0.5 0.5)
#   dblclick [x y]                      a double click as a browser reports it: down, up, down, up, then the page's
#                                       "MouseDouble" message (and no release after it, as on E3DS's page)
#   dbl [button] [x y]                  the "MouseDouble" message alone
#   down <button> [x y] / up <button> [x y]     button 0 left, 1 middle, 2 right
#   mouse <dx> <dy> [events] [gap ms]   that many mouse events of dx, dy browser pixels each (default 1 event, 16 ms apart)
#   key <keyCode> [hold ms]             a JavaScript keyCode down, then up (P 80, Enter 13, Esc 27, W 87, Space 32, arrows 37..40)
#   keydown <keyCode> / keyup <keyCode>
#   cmd <console command>               {"ConsoleCommand": "..."}, what a page's emitConsoleCommand sends
#   res <width> <height>                {"Resolution.Width": w, "Resolution.Height": h}, the page's size request
#   pad connect                         a gamepad appears (the game answers with its id)
#   pad axis <n> <value> [seconds]      n: 1 left X, 2 left Y, 3 right X, 4 right Y (up is +), 5 left trigger, 6 right trigger;
#                                       sent 60 times a second for that long (default one message), as a browser does
#   pad button <n> [hold ms] [first]    the browser's button index (0 A, 1 B, 2 X, 3 Y, 9 Start, 10 L3, 12..15 D-pad),
#                                       sent again every frame while held, marked as a repeat from the second message
#                                       on; with the word "first" the first message is marked as a repeat too: the
#                                       first press of a page's session (a browser shows the pad to the page only once
#                                       a button is down, and the page then takes that button for held already)
#   frame <file.jpg>                    save the next video frame (into --out)
# It prints one line per step and a count of video frames every 5 s; it ends with the script. "repeats" in that line
# counts received frames that show the same picture as the frame before (a sample of 2,000 points of the picture's
# brightness differs by less than half a level): while the view turns, a repeat is a frame sent twice, not a new one.
#
# rtcaudio.py (the listening tool) is this viewer with a recorder on the received sound: it imports this file, so
# both play a script with the same code. It sets hooks['audio'] (called with every decoded audio frame) and
# hooks['action'] (called with the time and the text of every script line as it is sent).
import argparse, asyncio, json, struct, sys, time

import websockets
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp

ap = argparse.ArgumentParser()
ap.add_argument('streamer')
ap.add_argument('script')
ap.add_argument('--player', default='')
ap.add_argument('--out', default='.')
ap.add_argument('--port', type=int, default=8090)
ap.add_argument('--nodecode', action='store_true')
ap.add_argument('--delay-ms', type=float, default=0.0)
ap.add_argument('--link-kbps', type=float, default=0.0)
ap.add_argument('--link-queue-ms', type=float, default=150.0)
ap.add_argument('--remb-kbps', type=float, default=0.0)
A = ap.parse_args()

link = {'dropped': 0, 'passed': 0, 'bytes': 0, 'maxq': 0.0}


def install_link():
    """The viewer's own link (see the header): delay both ways, a rate-limited drop-tail downlink, a fixed REMB."""
    import aioice.ice as ice
    if A.delay_ms > 0 or A.link_kbps > 0:
        half = A.delay_ms / 2000.0
        rate = A.link_kbps * 1000.0
        queue = A.link_queue_ms / 1000.0
        free = [0.0]  # the loop time at which the downlink has sent everything queued so far
        real_received, real_send_data, real_send_stun = ice.StunProtocol.datagram_received, ice.StunProtocol.send_data, ice.StunProtocol.send_stun

        def received(self, data, addr):
            loop = asyncio.get_running_loop()
            now = loop.time()
            at = now
            if rate > 0:
                start = max(now, free[0])
                link['maxq'] = max(link['maxq'], start - now)
                if start - now > queue:
                    link['dropped'] += 1
                    return
                at = start + len(data) * 8 / rate
                free[0] = at
            link['passed'] += 1
            link['bytes'] += len(data)
            due = at + half - now
            if due <= 0.0005:
                real_received(self, data, addr)
            else:
                loop.call_later(due, real_received, self, data, addr)

        def later_send(self, data, addr):
            try:
                self.transport.sendto(data, addr)
            except Exception:
                pass  # the connection was closed while the packet was on its way

        async def send_data(self, data, addr):
            if half <= 0.0005:
                return await real_send_data(self, data, addr)
            asyncio.get_running_loop().call_later(half, later_send, self, data, addr)

        def send_stun(self, message, addr):
            if half <= 0.0005:
                return real_send_stun(self, message, addr)
            asyncio.get_running_loop().call_later(half, later_send, self, bytes(message), addr)

        ice.StunProtocol.datagram_received = received
        ice.StunProtocol.send_data = send_data
        ice.StunProtocol.send_stun = send_stun
    if A.remb_kbps > 0:
        import aiortc.rate as rate_module
        real_add = rate_module.RemoteBitrateEstimator.add

        def add(self, *args, **kwargs):
            r = real_add(self, *args, **kwargs)
            return None if r is None else (int(A.remb_kbps * 1000), r[1])

        rate_module.RemoteBitrateEstimator.add = add


install_link()

if A.nodecode:
    # The receiver hands every complete video frame to a decoder of our own, which counts it and decodes nothing.
    import aiortc.rtcrtpreceiver as _receiver

    _real_decoder = _receiver.get_decoder

    class _CountOnly:
        def decode(self, encoded_frame):
            st['video'] += 1
            return []

    _receiver.get_decoder = lambda codec: _CountOnly() if codec.mimeType.lower().startswith('video/') else _real_decoder(codec)

t0 = time.time()
st = {'video': 0, 'audio': 0, 'size': None, 'channel': None, 'pad': None, 'want_frame': None, 'messages': 0, 'repeats': 0, 'sig': None}
hooks = {'audio': None, 'action': None}


def log(*a):
    print(f'{time.time() - t0:8.3f}', *a, flush=True)


def int16(v):
    """DataView.setInt16: the fraction is cut, the value wraps into 16 bits."""
    v = int(v) % 65536
    return v - 65536 if v >= 32768 else v


def uint16(v):
    return int(v) % 65536


class Player:
    """The page's side of the mouse: a pointer-locked cursor that starts in the middle (MouseControllerLocked.ts)."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.x, self.y = w / 2, h / 2

    def pos(self, fx=None, fy=None):
        if fx is not None:
            self.x, self.y = fx * self.w, fy * self.h
        return uint16(self.x / self.w * 65536), uint16(self.y / self.h * 65536)

    def move(self, dx, dy):
        self.x = (self.x + dx) % self.w
        self.y = (self.y + dy) % self.h
        # InputCoordTranslator.ts translateSigned, player and video of the same shape.
        return struct.pack('<BHHhh', 74, *self.pos(), int16(dx / (0.5 * self.w) * 32767), int16(dy / (0.5 * self.h) * 32767))


def descriptor(kind, text):
    return bytes([kind]) + struct.pack('<H', len(text)) + text.encode('utf-16-le')


async def play(lines, send, player):
    for raw in lines:
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        w = line.split()
        verb, a = w[0], w[1:]
        if verb == 'wait':
            await asyncio.sleep(float(a[0]))
            continue
        log('>', line)
        if hooks['action']:
            hooks['action'](time.time() - t0, line)
        if verb == 'say':
            pass
        elif verb == 'dblclick':
            x, y = player.pos(float(a[0]), float(a[1])) if len(a) >= 2 else player.pos()
            for _ in range(2):
                send(struct.pack('<BBHH', 72, 0, x, y))
                await asyncio.sleep(0.06)
                send(struct.pack('<BBHH', 73, 0, x, y))
                await asyncio.sleep(0.06)
            send(struct.pack('<BBHH', 76, 0, x, y))
        elif verb == 'dbl':
            button = int(a[0]) if a else 0
            x, y = player.pos(float(a[1]), float(a[2])) if len(a) >= 3 else player.pos()
            send(struct.pack('<BBHH', 76, button, x, y))
        elif verb in ('click', 'down', 'up'):
            button = 0 if verb == 'click' else int(a[0])
            at = a if verb == 'click' else a[1:]
            x, y = player.pos(float(at[0]), float(at[1])) if len(at) >= 2 else player.pos()
            if verb in ('click', 'down'):
                send(struct.pack('<BBHH', 72, button, x, y))
            if verb == 'click':
                await asyncio.sleep(0.08)
            if verb in ('click', 'up'):
                send(struct.pack('<BBHH', 73, button, x, y))
        elif verb == 'mouse':
            dx, dy = float(a[0]), float(a[1])
            n = int(a[2]) if len(a) > 2 else 1
            gap = float(a[3]) / 1000 if len(a) > 3 else 0.016
            for i in range(n):
                send(player.move(dx, dy))
                if i + 1 < n:
                    await asyncio.sleep(gap)
        elif verb == 'key':
            send(struct.pack('<BBB', 60, int(a[0]), 0))
            await asyncio.sleep(float(a[1]) / 1000 if len(a) > 1 else 0.08)
            send(struct.pack('<BB', 61, int(a[0])))
        elif verb == 'keydown':
            send(struct.pack('<BBB', 60, int(a[0]), 0))
        elif verb == 'keyup':
            send(struct.pack('<BB', 61, int(a[0])))
        elif verb == 'cmd':
            send(descriptor(51, json.dumps({'ConsoleCommand': line.split(None, 1)[1]})))
        elif verb == 'res':
            send(descriptor(51, json.dumps({'Resolution.Width': int(a[0]), 'Resolution.Height': int(a[1])})))
        elif verb == 'pad' and a[0] == 'connect':
            send(bytes([93]))
            for _ in range(40):
                if st['pad'] is not None:
                    break
                await asyncio.sleep(0.05)
            log('pad id', st['pad'])
        elif verb == 'pad' and a[0] == 'axis':
            pad = st['pad'] or 0
            secs = float(a[3]) if len(a) > 3 else 0
            until = time.time() + secs
            while True:
                send(struct.pack('<BBBd', 92, pad, int(a[1]), float(a[2])))
                if time.time() >= until:
                    break
                await asyncio.sleep(1 / 60)
        elif verb == 'pad' and a[0] == 'button':
            pad = st['pad'] or 0
            hold = float(a[2]) / 1000 if len(a) > 2 and a[2] != 'first' else 0.1
            until = time.time() + hold
            repeat = 1 if 'first' in a[2:] else 0
            while time.time() < until:
                send(struct.pack('<BBBB', 90, pad, int(a[1]), repeat))
                repeat = 1
                await asyncio.sleep(1 / 60)
            send(struct.pack('<BBBB', 91, pad, int(a[1]), 0))
        elif verb == 'frame' and A.nodecode:
            log('not decoding: no frame saved')
        elif verb == 'frame':
            st['want_frame'] = f'{A.out}/{a[0]}'
            for _ in range(100):
                if st['want_frame'] is None:
                    break
                await asyncio.sleep(0.05)
        else:
            log('unknown script line:', line)


async def main():
    lines = (sys.stdin if A.script == '-' else open(A.script)).read().splitlines()
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    ready = asyncio.Event()

    async def consume(track):
        while True:
            try:
                fr = await track.recv()
            except Exception as e:
                log('track ended', track.kind, type(e).__name__)
                return
            if track.kind != 'video':
                st['audio'] += 1
                if hooks['audio']:
                    hooks['audio'](fr)
                continue
            st['video'] += 1
            try:
                plane = memoryview(fr.planes[0])
                sig = bytes(plane[::max(1, len(plane) // 2000)])
                if st['sig'] is not None and len(sig) == len(st['sig']) and sum(abs(a - b) for a, b in zip(sig, st['sig'])) < 0.5 * len(sig):
                    st['repeats'] += 1
                st['sig'] = sig
            except Exception:  # the count is a help, not the test
                pass
            if st['size'] != [fr.width, fr.height]:
                st['size'] = [fr.width, fr.height]
                log('video', st['size'])
            if st['want_frame']:
                fr.to_image().save(st['want_frame'], quality=88)
                log('saved', st['want_frame'], st['size'])
                st['want_frame'] = None
            if st['video'] >= 5 and st['channel'] is not None and st['channel'].readyState == 'open':
                ready.set()

    @pc.on('track')
    def on_track(track):
        asyncio.ensure_future(consume(track))

    @pc.on('connectionstatechange')
    async def on_state():
        log('connection', pc.connectionState)

    @pc.on('datachannel')
    def on_channel(ch):
        log('data channel', ch.label)
        st['channel'] = ch

        @ch.on('message')
        def on_message(m):
            st['messages'] += 1
            if isinstance(m, (bytes, bytearray)) and len(m) >= 2 and m[0] == 13:
                # GamepadResponse: a UTF-16 JSON string, {"controllerId": n}; the pad's messages carry that id.
                try:
                    st['pad'] = int(json.loads(bytes(m[1:]).decode('utf-16-le'))['controllerId'])
                except (ValueError, KeyError):
                    log('gamepad response not understood:', bytes(m[:40]))

    def send(data):
        ch = st['channel']
        if ch is None or ch.readyState != 'open':
            log('no data channel: message dropped')
            return
        ch.send(data)

    async with websockets.connect(f'ws://127.0.0.1:{A.port}', max_size=None) as ws:
        async def reader():
            async for m in ws:
                msg = json.loads(m)
                t = msg.get('type')
                if t == 'config':
                    await ws.send(json.dumps({'type': 'listStreamers'}))
                elif t == 'streamerList':
                    log('streamers', msg.get('ids'), f'(wall clock {time.time():.3f}: subscribing now)')
                    await ws.send(json.dumps({'type': 'subscribe', 'streamerId': A.streamer}))
                elif t == 'offer':
                    await pc.setRemoteDescription(RTCSessionDescription(sdp=msg['sdp'], type='offer'))
                    await pc.setLocalDescription(await pc.createAnswer())
                    await ws.send(json.dumps({'type': 'answer', 'sdp': pc.localDescription.sdp}))
                elif t == 'iceCandidate':
                    c = msg.get('candidate') or {}
                    if c.get('candidate'):
                        cand = candidate_from_sdp(c['candidate'].split(':', 1)[1])
                        cand.sdpMid = c.get('sdpMid')
                        cand.sdpMLineIndex = c.get('sdpMLineIndex')
                        try:
                            await pc.addIceCandidate(cand)
                        except Exception as e:
                            log('addIceCandidate', e)
                elif t == 'ping':
                    # The signalling server drops a player that does not answer its pings (after about a minute).
                    await ws.send(json.dumps({'type': 'pong', 'time': msg.get('time')}))

        async def counter():
            while True:
                await asyncio.sleep(5)
                log('frames', st['video'], 'audio', st['audio'], 'messages from the game', st['messages'], 'repeats', st['repeats'])
                if A.link_kbps > 0 or A.delay_ms > 0:
                    log('link: passed', link['passed'], 'dropped', link['dropped'], 'bytes', link['bytes'], 'longest queue', round(link['maxq'] * 1000), 'ms')

        async def undecoded():  # --nodecode: no decoded frame ever says that the video has started
            while not ready.is_set():
                if st['video'] >= 5 and st['channel'] is not None and st['channel'].readyState == 'open':
                    st['size'] = st['size'] or [1920, 1080]
                    ready.set()
                await asyncio.sleep(0.1)

        tasks = [asyncio.ensure_future(reader()), asyncio.ensure_future(counter())]
        if A.nodecode:
            tasks.append(asyncio.ensure_future(undecoded()))
        try:
            await asyncio.wait_for(ready.wait(), 40)
        except asyncio.TimeoutError:
            log('NO VIDEO or no data channel after 40 s', json.dumps({k: st[k] for k in ('video', 'audio', 'size')}))
            for t in tasks:
                t.cancel()
            await pc.close()
            sys.exit(1)
        w, h = (int(v) for v in A.player.lower().split('x')) if A.player else st['size']
        log('playing; player', [w, h], 'video', st['size'])
        await play(lines, send, Player(w, h))
        await asyncio.sleep(0.3)
        log('END', json.dumps({k: st[k] for k in ('video', 'audio', 'size', 'pad', 'messages', 'repeats')}))
        for t in tasks:
            t.cancel()
    await pc.close()


if __name__ == '__main__':
    asyncio.run(main())
