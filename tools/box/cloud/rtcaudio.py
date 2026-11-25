# The listening tool: the viewer of rtcinput.py with a recorder on the sound it receives. Nobody on the box has ears,
# so the game's sound through the stream is proven by measurement: what arrived, when, how loud. It plays the same
# viewer scripts as rtcinput.py (it imports that file: same messages, same timing) and
#
#   - writes the received sound to a WAV (stereo, 48 kHz, 16 bit), every decoded Opus frame at the place its RTP
#     timestamp gives it, so a lost packet leaves a hole of the right length instead of shortening the recording;
#   - prints one line per half second: loudness (RMS) and peak in dBFS, clipped samples (at 99 % of full scale or
#     more: a lower bound, because the Opus decoder rounds a clipped top off; the peak is the surer sign), digital
#     silence, lost sound, the size of the Opus packets (silence is 3 bytes a packet; the game's sound is hundreds);
#   - counts drop-outs: 10 ms to 1 s of digital silence with sound right before and right after it (a mixer that
#     starves or a sender that had nothing to send; the game's music and street never stop, so there is no such
#     silence in a healthy stream), and compares the sound's own clock with the wall clock;
#   - notes the time of every script line it sends, and the arrival time of every sound packet, in <wav>.json, so
#     audio_find.py can say how long after a fire input the gun's sound started.
#
#   python rtcaudio.py <streamerId> <script file or -> [--wav sound.wav] [rtcinput.py's options]
#   python rtcaudio.py --read <sound.wav>            the half-second lines and the summary again, from a recording
#   python rtcaudio.py --selftest <folder> [--audio <Content/Audio>]
#                                                    the instrument checked without the game: a sender in this process
#                                                    sends a known signal (a 1 kHz tone at a known level, a gap, a
#                                                    clipped burst, a real sample of the game at known times, levels
#                                                    and pitches over a music bed, and a sample started by each script
#                                                    action) through Opus, RTP and this recorder; it prints what it can
#                                                    check itself, and audio_find.py --truth checks the rest
#
# Runs in the viewer's Python (/tmp/fps/venv on the box: aiortc, no numpy). Times in the lines: "at" is the sound's own
# clock (seconds from the first packet), "arrived" is when the packet that holds that moment came in, on the wall clock
# rtcinput.py's lines use (seconds from the start).
import argparse
import array
import bisect
import json
import math
import os
import signal
import struct
import sys
import time
import wave

RATE = 48000
HALF = RATE // 2          # frames in half a second
SUB = RATE // 100         # frames in 10 ms: the grain of the silence and drop-out search
QUIET = 3                 # a 10 ms grain whose samples all lie within +-3 of zero is digital silence
HOLE = 16                 # ... within +-16 (-66 dBFS): the codec's ringing at the edge of a silence
LOUD = 64                 # about -54 dBFS: what "sound right before and after" a drop-out means
FULL = 32440              # 99 % of full scale: a clipped sample (the Opus decoder rounds a clipped top off)


def db(v):
    return -120.0 if v <= 0 else 20 * math.log10(v / 32768.0)


class Recorder:
    """The received sound on its own clock, written as it comes, measured per half second."""

    def __init__(self, path, log=print, clock=time.time):
        self.path, self.log, self.clock = path, log, clock
        self.w = wave.open(path, 'wb')
        self.w.setnchannels(2)
        self.w.setsampwidth(2)
        self.w.setframerate(RATE)
        self.first_pts = None
        self.frames = 0            # frames written: the position of the next sample on the sound's clock
        self.pending = array.array('h')
        self.pending_lost = 0
        self.rows, self.gaps, self.actions, self.packets = [], [], [], []
        self.first_raw = None
        self.lost = self.clipped = self.silent = self.late = 0
        self.sum_sq = 0.0
        self.peak = 0
        # Drop-outs: the hole being followed (grains within +-HOLE), the loudest of the three grains before it, and
        # the hole that waits for the three grains after it.
        self.hole = None           # [start frame, frames, has a grain of digital silence, loudest before]
        self.recent = []
        self.waiting = None        # [start, frames, loudest before, grains seen after, loudest after]
        self.closed = False
        self.note = ''

    # -- what the hooks call

    def packet(self, raw_ts, size):
        """Every audio RTP packet as it arrives (before the jitter buffer): its place on the sound's clock, the time."""
        if self.first_raw is None:
            self.first_raw = raw_ts
        self.packets.append(((raw_ts - self.first_raw) & 0xFFFFFFFF, round(self.clock(), 4), size))

    def action(self, t, line):
        self.actions.append((round(t, 4), line))

    def frame(self, fr):
        """A decoded frame (PyAV AudioFrame, 16-bit interleaved)."""
        try:
            if fr.format.name != 's16' or fr.sample_rate != RATE:
                self.note = f'unexpected sound format {fr.format.name} at {fr.sample_rate} Hz'
                return
            ch = len(fr.layout.channels)
            data = array.array('h')
            data.frombytes(bytes(memoryview(fr.planes[0])[:fr.samples * ch * 2]))
            if ch == 1:
                both = array.array('h', bytes(len(data) * 4))
                both[0::2] = data
                both[1::2] = data
                data = both
            elif ch != 2:
                self.note = f'unexpected sound layout {fr.layout.name}'
                return
            self.put(fr.pts, data)
        except Exception as e:  # the recorder must never stop the viewer
            self.note = f'recorder: {e!r}'

    # -- the recording

    def put(self, pts, data):
        """Interleaved stereo samples whose first frame has the time stamp pts (in frames; None: right after the last)."""
        if self.first_pts is None:
            self.first_pts = pts if pts is not None else 0
        pos = self.frames if pts is None else pts - self.first_pts
        if pos > self.frames:      # packets that never came: a hole of their length
            hole = pos - self.frames
            self.lost += hole
            self.pending_lost += hole
            self._add(array.array('h', bytes(hole * 4)))
        elif pos < self.frames:    # a frame that overlaps what is written (a duplicate, or one that came too late)
            cut = self.frames - pos
            self.late += min(cut, len(data) // 2)
            data = data[cut * 2:]
        if len(data):
            self._add(data)

    def _add(self, data):
        self.w.writeframesraw(data.tobytes())
        self.frames += len(data) // 2
        self.pending.extend(data)
        while len(self.pending) >= HALF * 2:
            self._row(self.pending[:HALF * 2])
            del self.pending[:HALF * 2]

    def arrival(self, pos):
        """When the packet that holds this place on the sound's clock arrived."""
        if not self.packets:
            return None
        return self.packets[max(0, bisect.bisect_right(self.packets, (pos, float('inf'), 0)) - 1)][1]

    def _row(self, buf):
        n = len(buf)
        at = self.frames - len(self.pending) // 2   # the row is the front of pending, which ends at frames
        hi, lo = max(buf), min(buf)
        peak = max(hi, -lo)
        sq = sum(v * v for v in buf)
        clipped = sum(1 for v in buf if v >= FULL or v <= -FULL) if peak >= FULL else 0
        silent = 0
        for k in range(0, n, SUB * 2):
            grain = buf[k:k + SUB * 2]
            g = max(max(grain), -min(grain))
            if g <= QUIET:
                silent += len(grain) // 2
            self._grain(at + k // 2, len(grain) // 2, g)
        self.sum_sq += sq
        self.peak = max(self.peak, peak)
        self.clipped += clipped
        self.silent += silent
        a, b = at, at + n // 2
        sizes = [p[2] for p in self.packets[bisect.bisect_left(self.packets, (a, 0, 0)):bisect.bisect_left(self.packets, (b, 0, 0))]]
        row = {
            'at': round(a / RATE, 3), 'arrived': self.arrival(a), 'rms': round(db(math.sqrt(sq / max(1, n))), 1), 'peak': round(db(peak), 1),
            'clipped': clipped, 'silentMs': round(1000 * silent / RATE), 'lostMs': round(1000 * self.pending_lost / RATE),
            'bytes': round(sum(sizes) / len(sizes), 1) if sizes else None,
        }
        self.pending_lost = 0
        self.rows.append(row)
        arrived = f"arrived {row['arrived']:8.3f}" if row['arrived'] is not None else ''
        size = f"  {row['bytes']:.0f} bytes a packet" if row['bytes'] is not None else ''
        self.log(f"sound at {row['at']:7.2f} s  {arrived}  rms {row['rms']:6.1f} dBFS  peak {row['peak']:6.1f} dBFS  clipped {clipped}"
                 f"  silent {row['silentMs']} ms  lost {row['lostMs']} ms{size}")

    def _grain(self, pos, frames, peak):
        """The drop-out search, one 10 ms grain at a time: a hole is 10 ms to 1 s within +-HOLE that holds digital
        silence and has sound (LOUD or more) in the three grains before it and in the three after it."""
        if self.waiting is not None:
            w = self.waiting
            w[3] += 1
            w[4] = max(w[4], peak)
            if w[3] >= 3 or peak <= HOLE:
                if w[2] >= LOUD and w[4] >= LOUD:
                    self.gaps.append((round(w[0] / RATE, 3), round(1000 * w[1] / RATE)))
                self.waiting = None
        if peak <= HOLE:
            if self.hole is None:
                self.hole = [pos, 0, False, max(self.recent, default=0)]
            self.hole[1] += frames
            self.hole[2] = self.hole[2] or peak <= QUIET
        else:
            if self.hole is not None:
                h = self.hole
                if h[2] and SUB <= h[1] <= RATE:
                    self.waiting = [h[0], h[1], h[3], 1, peak]
                self.hole = None
            self.recent = (self.recent + [peak])[-3:]

    def summary(self):
        n = self.frames * 2
        secs = self.frames / RATE
        s = {
            'seconds': round(secs, 3), 'rms': round(db(math.sqrt(self.sum_sq / max(1, n))), 1), 'peak': round(db(self.peak), 1),
            'clipped': self.clipped, 'silentSeconds': round(self.silent / RATE, 2), 'lostMs': round(1000 * self.lost / RATE),
            'lateMs': round(1000 * self.late / RATE), 'dropOuts': len(self.gaps),
            'longestDropOutMs': max((g[1] for g in self.gaps), default=0), 'packets': len(self.packets),
        }
        if len(self.packets) > 100:
            # The sound's clock against the wall clock, between the first and the last packet: a sender whose mixer
            # falls behind real time sends less than a second of sound a second.
            span = self.packets[-1][1] - self.packets[0][1]
            s['soundPerWallSecond'] = round((self.packets[-1][0] - self.packets[0][0]) / RATE / span, 4) if span > 0 else None
            gaps = sorted(b[1] - a[1] for a, b in zip(self.packets, self.packets[1:]))
            s['longestWaitForAPacketMs'] = round(1000 * gaps[-1])
        return s

    def close(self):
        if self.closed:
            return
        self.closed = True
        if len(self.pending):
            self._row(self.pending)
        if self.waiting is not None and self.waiting[2] >= LOUD and self.waiting[4] >= LOUD:
            self.gaps.append((round(self.waiting[0] / RATE, 3), round(1000 * self.waiting[1] / RATE)))
        self.w.close()
        s = self.summary()
        meta = {'rate': RATE, 'summary': s, 'rows': self.rows, 'dropOuts': self.gaps, 'actions': self.actions, 'packets': self.packets, 'note': self.note}
        with open(self.path + '.json', 'w') as f:
            json.dump(meta, f)
        self.log(f"SOUND {s['seconds']:.1f} s recorded in {self.path}: rms {s['rms']} dBFS, peak {s['peak']} dBFS, clipped samples {s['clipped']}, "
                 f"digital silence {s['silentSeconds']} s, lost {s['lostMs']} ms, drop-outs {s['dropOuts']} (longest {s['longestDropOutMs']} ms)"
                 + (f", {s['soundPerWallSecond']} s of sound a second of wall clock, longest wait for a packet {s['longestWaitForAPacketMs']} ms" if 'soundPerWallSecond' in s else '')
                 + (f"; {self.note}" if self.note else ''))
        for at, ms in self.gaps[:20]:
            self.log(f'drop-out at {at:.3f} s: {ms} ms of digital silence inside sound')


def hook_packets(rec):
    """Every audio RTP packet's arrival, before aiortc's jitter buffer (which holds a frame back until four more have
    come: about 80 ms that a script action's delay must not be charged with)."""
    import aiortc.rtcrtpreceiver as R

    real = R.RTCRtpReceiver._handle_rtp_packet

    async def handle(self, packet, arrival_time_ms):
        if getattr(self, '_RTCRtpReceiver__kind', None) == 'audio':
            rec.packet(packet.timestamp, len(packet.payload))
        return await real(self, packet, arrival_time_ms)

    R.RTCRtpReceiver._handle_rtp_packet = handle


def read(path):
    """The lines and the summary again from a recording (stereo, 48 kHz, 16 bit)."""
    out = path + '.reread.wav'
    r = Recorder(out, log=print, clock=lambda: 0.0)
    with wave.open(path, 'rb') as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (2, 2, RATE):
            sys.exit(f'{path}: not a stereo 16-bit 48 kHz recording')
        while True:
            b = w.readframes(RATE)
            if not b:
                break
            a = array.array('h')
            a.frombytes(b)
            r.put(None, a)
    r.close()
    os.remove(out)
    os.remove(out + '.json')


# ---------------------------------------------------------------------------------------------------- the self-test

def read_wav_mono(path):
    """A WAV of the game's library (PCM 16, 24 or 32 bit, or 32-bit float; any channel count) as mono floats."""
    with open(path, 'rb') as f:
        b = f.read()
    if b[:4] != b'RIFF' or b[8:12] != b'WAVE':
        raise ValueError(f'{path}: not a WAV')
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], struct.unpack('<I', b[i + 4:i + 8])[0]
        if tag == b'fmt ':
            fmt = b[i + 8:i + 8 + size]
        elif tag == b'data':
            data = b[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)
    kind, ch, rate, _, _, bits = struct.unpack('<HHIIHH', fmt[:16])
    if kind == 0xFFFE:
        kind = struct.unpack('<H', fmt[24:26])[0]
    step = bits // 8
    n = len(data) // (step * ch)
    out = []
    if kind == 3 and bits == 32:
        v = struct.unpack(f'<{n * ch}f', data[:n * ch * 4])
        out = [sum(v[k:k + ch]) / ch for k in range(0, n * ch, ch)]
    elif kind == 1:
        scale = float(1 << (bits - 1))
        for k in range(n):
            s = 0
            for c in range(ch):
                o = (k * ch + c) * step
                s += int.from_bytes(data[o:o + step], 'little', signed=bits > 8)
            out.append(s / ch / scale)
    else:
        raise ValueError(f'{path}: WAV format {kind} with {bits} bits is not read')
    return rate, out


def selftest(folder, audio_dir):
    import asyncio
    import fractions

    import av
    from aiortc import RTCPeerConnection
    from aiortc.mediastreams import MediaStreamTrack

    os.makedirs(folder, exist_ok=True)
    t0 = time.time()

    def log(*a):
        print(f'{time.time() - t0:8.3f}', *a, flush=True)

    # The known signal, mono floats at 48 kHz (sent on both channels).
    total = 22 * RATE
    x = [0.0] * total
    truth = {'tone': {'from': 1.0, 'to': 3.0, 'hz': 1000, 'peak': 0.1}, 'planted': [], 'gap': {'at': 12.0, 'ms': 100},
             'clip': {'at': 14.0, 'ms': 20}, 'actions': []}
    for n in range(1 * RATE, 3 * RATE):
        x[n] = 0.1 * math.sin(2 * math.pi * 1000 * n / RATE)
    bed_file = os.path.join(audio_dir, 'Web', 'stem_keys_01.wav')
    shot_file = os.path.join(audio_dir, 'Gen', 'chopper_close_01.wav')
    click_file = os.path.join(audio_dir, 'Gen', 'nine_close_01.wav')
    def at48(path, seconds=None):
        # The library's files are 11 to 48 kHz (the web game's own rates): brought to 48 kHz as the engine plays them.
        rate, v = read_wav_mono(path)
        if seconds:
            v = v[:int(seconds * rate) + 2]
        if rate == RATE:
            return v
        out, step = [], rate / RATE
        for k in range(int((len(v) - 1) / step)):
            p = k * step
            i = int(p)
            out.append(v[i] + (v[i + 1] - v[i]) * (p - i))
        return out

    bed = at48(bed_file, 17.0)
    shot = at48(shot_file)
    click = at48(click_file)
    bed_peak = max(abs(v) for v in bed) or 1.0
    bed_gain = 0.05 / bed_peak    # a quiet bed under the planted samples, as the music is under the guns
    street = at48(os.path.join(audio_dir, 'Web', 'bed_day_01.wav'), 17.0)
    street_gain = 0.03 / (max(abs(v) for v in street) or 1.0)
    for n in range(int(3.5 * RATE), 20 * RATE):
        x[n] += bed_gain * bed[(n - int(3.5 * RATE)) % len(bed)] + street_gain * street[(n - int(3.5 * RATE)) % len(street)]
    truth['bed'] = {'file': os.path.relpath(bed_file, audio_dir), 'from': 3.5, 'to': 20.0, 'gain': round(bed_gain, 5)}

    def plant(sample, at, gain, speed):
        start = int(at * RATE)
        m = int(len(sample) / speed)
        for k in range(m):
            p = k * speed
            i = int(p)
            v = sample[i] + (sample[i + 1] - sample[i]) * (p - i) if i + 1 < len(sample) else sample[i]
            if start + k < total:
                x[start + k] += gain * v
        return start

    for at, gain, speed in ((6.0, 0.5, 1.0), (8.0, 0.25, 0.97), (10.0, 0.125, 1.03)):
        plant(shot, at, gain, speed)
        truth['planted'].append({'file': os.path.relpath(shot_file, audio_dir), 'at': at, 'gain': gain, 'rate': speed})
    for n in range(12 * RATE, int(12.1 * RATE)):
        x[n] = 0.0
    for n in range(14 * RATE, int(14.02 * RATE)):
        x[n] = 1.0 if (n // 48) % 2 == 0 else -1.0   # a 500 Hz square at full scale: 960 clipped samples a channel
    truth['clickFile'] = os.path.relpath(click_file, audio_dir)

    class Known(MediaStreamTrack):
        kind = 'audio'

        def __init__(self):
            super().__init__()
            self.n = 0
            self.start = None
            self.want = []       # the wall times of actions whose sample has not been placed yet

        async def recv(self):
            if self.start is None:
                self.start = time.time()
            wait = self.start + self.n * 0.02 - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
            a = self.n * 960
            for sent in self.want:     # an action arrived: its sample starts with this frame
                plant(click, a / RATE, 0.4, 1.0)
                truth['actions'].append({'sent': sent, 'at': round(a / RATE, 4), 'frameLeft': round(time.time() - t0, 4)})
            self.want = []
            seg = x[a:a + 960] if a + 960 <= total else [0.0] * 960
            pcm = array.array('h', bytes(960 * 4))
            ints = [max(-32768, min(32767, int(round(v * 32767)))) for v in seg]
            pcm[0::2] = array.array('h', ints)
            pcm[1::2] = array.array('h', ints)
            fr = av.AudioFrame(format='s16', layout='stereo', samples=960)
            fr.planes[0].update(pcm.tobytes())
            fr.pts = a
            fr.sample_rate = RATE
            fr.time_base = fractions.Fraction(1, RATE)
            self.n += 1
            return fr

    wav = os.path.join(folder, 'selftest.wav')
    rec = Recorder(wav, log=log, clock=lambda: time.time() - t0)
    hook_packets(rec)

    async def run():
        sender, viewer = RTCPeerConnection(), RTCPeerConnection()
        track = Known()
        sender.addTrack(track)
        channel = viewer.createDataChannel('input')

        @sender.on('datachannel')
        def on_channel(ch):
            @ch.on('message')
            def on_message(m):
                track.want.append(float(m))

        @viewer.on('track')
        def on_track(remote):
            async def consume():
                while True:
                    try:
                        rec.frame(await remote.recv())
                    except Exception:
                        return
            asyncio.ensure_future(consume())

        await viewer.setLocalDescription(await viewer.createOffer())  # the viewer offers: it owns the data channel
        await sender.setRemoteDescription(viewer.localDescription)
        await sender.setLocalDescription(await sender.createAnswer())
        await viewer.setRemoteDescription(sender.localDescription)
        while track.start is None:
            await asyncio.sleep(0.05)
        for at in (15.5, 16.75, 18.0):   # three "fire" actions, as a script would send them
            await asyncio.sleep(max(0, track.start + at - time.time()))
            now = round(time.time() - t0, 4)
            rec.action(now, 'down 0')
            channel.send(str(now))
            log('> down 0')
        await asyncio.sleep(max(0, track.start + 22.3 - time.time()))
        await sender.close()
        await viewer.close()

    # The viewer has nothing to send but must offer an audio line to receive on.
    real_offer = RTCPeerConnection.createOffer

    async def offer(self, *a, **k):
        if not self.getTransceivers():
            self.addTransceiver('audio', direction='recvonly')
        return await real_offer(self, *a, **k)

    RTCPeerConnection.createOffer = offer
    asyncio.run(run())
    rec.close()
    with open(os.path.join(folder, 'selftest-truth.json'), 'w') as f:
        json.dump(truth, f, indent=1)

    # What this file can check by itself: the tone's level and pitch, the gap, the clipped burst, nothing lost.
    with wave.open(wav, 'rb') as w:
        a = array.array('h')
        a.frombytes(w.readframes(w.getnframes()))
    left = a[0::2]
    onset = next((i for i, v in enumerate(left) if abs(v) > 600), None)
    ok = True

    def check(name, good, text):
        nonlocal ok
        ok = ok and good
        print(('PASS ' if good else 'FAIL ') + name + ': ' + text)

    check('the tone starts', onset is not None, f"at {onset / RATE if onset is not None else -1:.4f} s of the recording (sent at 1.0000 s; Opus adds 6.5 ms)")
    if onset is not None:
        shift = onset - RATE
        mid = left[onset + RATE // 2:onset + RATE + RATE // 2]
        rms = math.sqrt(sum(v * v for v in mid) / len(mid))
        crossings = sum(1 for p, q in zip(mid, mid[1:]) if p < 0 <= q)
        check('the tone\'s level', abs(db(rms) - (-23.01)) < 0.5, f'{db(rms):.2f} dBFS RMS received, -23.01 sent (peak 0.1)')
        check('the tone\'s pitch', abs(crossings - 1000) <= 2, f'{crossings} cycles in a second, 1000 sent')
        gap = [g for g in rec.gaps if abs(g[0] - shift / RATE - 12.0) < 0.03]
        check('the 100 ms gap', bool(gap) and 60 <= gap[0][1] <= 110, f"found {gap[0] if gap else rec.gaps} (at 12.0 s for 100 ms, sent; the codec rings into its ends)")
        burst = left[14 * RATE + shift - 480:14 * RATE + shift + 1440]
        clipped = sum(1 for v in burst if abs(v) >= FULL)
        check('the clipped burst', clipped >= 10 and rec.clipped >= 2 * clipped - 4 and rec.peak >= 32767,
              f'{clipped} samples at 99 % of full scale or more on one channel in the burst (960 were sent so: Opus keeps the edges and rounds the tops off, '
              f'so the count is a lower bound), {rec.clipped} counted in all, peak {db(rec.peak):.1f} dBFS')
    s = rec.summary()
    check('nothing lost', s['lostMs'] == 0, f"{s['lostMs']} ms lost, {s['packets']} packets")
    check('the sound\'s clock', abs((s.get('soundPerWallSecond') or 0) - 1) < 0.01, f"{s.get('soundPerWallSecond')} s of sound a second of wall clock")
    print(('SELFTEST PART 1 PASSED' if ok else 'SELFTEST PART 1 FAILED') + f': now run audio_find.py {wav} --truth {os.path.join(folder, "selftest-truth.json")} --audio {audio_dir}')
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--wav', default='')
    ap.add_argument('--read', default='')
    ap.add_argument('--selftest', default='')
    ap.add_argument('--audio', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'unreal', 'MurderInc', 'Content', 'Audio'))
    ours, rest = ap.parse_known_args()
    if ours.read:
        return read(ours.read)
    if ours.selftest:
        return selftest(ours.selftest, ours.audio)
    sys.argv = [sys.argv[0]] + rest
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rtcinput as V  # parses the rest of the command line as rtcinput.py does

    wav = ours.wav or os.path.join(V.A.out, 'sound.wav')
    rec = Recorder(wav, log=V.log, clock=lambda: time.time() - V.t0)
    V.hooks['audio'] = rec.frame
    V.hooks['action'] = rec.action
    hook_packets(rec)

    def stop(*_):
        raise SystemExit(143)   # the test's time limit (timeout sends SIGTERM): the recording is still written

    signal.signal(signal.SIGTERM, stop)
    try:
        V.asyncio.run(V.main())
    finally:
        rec.close()


if __name__ == '__main__':
    main()
