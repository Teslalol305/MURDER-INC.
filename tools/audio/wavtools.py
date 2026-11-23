"""Small WAV helpers for the audio scripts (numpy only): read any PCM/float WAV, write 24-bit, BS.1770 loudness."""
import struct
import wave

import numpy as np


def read(path):
    """(samples float64 [frames, channels], rate)."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        raise ValueError(f'{path}: not a WAVE file')
    pos, fmt, raw = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack('<I', data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b'fmt ':
            fmt = struct.unpack('<HHIIHH', body[:16])
            if fmt[0] == 0xFFFE and len(body) >= 26:
                fmt = (struct.unpack('<H', body[24:26])[0],) + fmt[1:]
        elif cid == b'data':
            raw = body
        pos += 8 + size + (size & 1)
    tag, ch, rate, _, _, bits = fmt
    if tag == 3:
        x = np.frombuffer(raw, dtype='<f4').astype(np.float64)
    elif bits == 16:
        x = np.frombuffer(raw, dtype='<i2') / 32768.0
    elif bits == 24:
        b = np.frombuffer(raw[:len(raw) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        x = v / 8388608.0
    elif bits == 32:
        x = np.frombuffer(raw, dtype='<i4') / 2147483648.0
    else:
        raise ValueError(f'{path}: {bits}-bit not supported')
    x = x[:len(x) // ch * ch].reshape(-1, ch)
    return x, rate


def write24(path, x, rate):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    v = np.clip(np.round(np.clip(x, -1, 1) * 8388607), -8388608, 8388607).astype(np.int32)
    b = np.empty((v.size, 3), dtype=np.uint8)
    flat = v.reshape(-1)
    b[:, 0] = flat & 255
    b[:, 1] = (flat >> 8) & 255
    b[:, 2] = (flat >> 16) & 255
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(3)
        w.setframerate(rate)
        w.writeframes(b.tobytes())


def resample(x, rate, to):
    """Linear-interpolation resample (placeholders only)."""
    if rate == to:
        return x
    n = int(round(len(x) * to / rate))
    t = np.arange(n) * rate / to
    if x.ndim == 1:
        return np.interp(t, np.arange(len(x)), x)
    return np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], axis=1)


def _response(b, a, n):
    """Frequency response of a biquad on an rfft grid of n points."""
    w = np.exp(-1j * np.pi * np.arange(n // 2 + 1) / (n // 2))
    return (b[0] + b[1] * w + b[2] * w * w) / (a[0] + a[1] * w + a[2] * w * w)


def _kweight48(x):
    """ITU-R BS.1770-4 K-weighting at 48 kHz, applied in the frequency domain (zero-padded, so no wrap)."""
    n = 1 << int(np.ceil(np.log2(len(x) + 4800)))
    h = _response([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], n)
    h *= _response([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], n)
    return np.fft.irfft(np.fft.rfft(x, n) * h, n)[:len(x)]


def lufs(x, rate=48000):
    """Integrated loudness (gated) of a mono signal at 48 kHz."""
    if rate != 48000:
        x = resample(x, rate, 48000)
    y = _kweight48(np.asarray(x, dtype=np.float64))
    block, hop = 19200, 4800
    zs = [np.mean(y[i:i + block] ** 2) for i in range(0, max(1, len(y) - block + 1), hop)] or [np.mean(y ** 2)]
    zs = np.array(zs)
    l = -0.691 + 10 * np.log10(zs + 1e-12)
    zs = zs[l > -70]
    if len(zs) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(zs)) - 10
    l = -0.691 + 10 * np.log10(zs + 1e-12)
    zs = zs[l > rel]
    return float(-0.691 + 10 * np.log10(np.mean(zs) + 1e-12))


def normalise(x, rate, target=-18.0, ceiling=-1.0):
    """Scale to the target integrated loudness, then pull the peak under the ceiling (dBFS)."""
    g = 10 ** ((target - lufs(x, rate)) / 20)
    y = x * g
    peak = np.max(np.abs(y)) + 1e-12
    top = 10 ** (ceiling / 20)
    if peak > top:
        y = y * (top / peak)
    return y


def trim(x, rate, threshold=0.04, pre=0.03, post=0.18):
    """Cut leading and trailing silence (relative threshold of the peak envelope), with fades."""
    env = np.abs(x)
    win = int(rate * 0.01)
    env = np.convolve(env, np.ones(win) / win, mode='same')
    on = np.where(env > threshold * env.max())[0]
    if len(on) == 0:
        return x
    a = max(0, on[0] - int(pre * rate))
    b = min(len(x), on[-1] + int(post * rate))
    y = x[a:b].copy()
    f = int(0.004 * rate)
    y[:f] *= np.linspace(0, 1, f)
    g = int(0.04 * rate)
    y[-g:] *= np.linspace(1, 0, g)
    return y
