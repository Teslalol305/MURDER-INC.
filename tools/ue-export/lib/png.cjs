'use strict';

// A small PNG reader and writer (8-bit RGB / RGBA, not interlaced: what a browser screenshot is), so the
// reference pictures can be made lighter without any dependency. `reduceLevels` rounds every colour
// channel to a few dozen evenly spaced levels: the picture looks the same (the largest change at 40
// levels is 3 parts in 255), but its rows compress far better than a renderer's full-depth noise.

const fs = require('node:fs');
const zlib = require('node:zlib');

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const CRC_TABLE = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  CRC_TABLE[n] = c >>> 0;
}

function crc32(...buffers) {
  let c = 0xffffffff;
  for (const buf of buffers) for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const paeth = (a, b, c) => {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
};

/** @returns {{width: number, height: number, channels: 3 | 4, data: Buffer}} rows top to bottom, no padding */
function decode(file) {
  const buf = Buffer.isBuffer(file) ? file : fs.readFileSync(file);
  if (!buf.subarray(0, 8).equals(SIGNATURE)) throw new Error('not a PNG');
  let width = 0;
  let height = 0;
  let channels = 0;
  const parts = [];
  for (let at = 8; at < buf.length; ) {
    const length = buf.readUInt32BE(at);
    const type = buf.toString('latin1', at + 4, at + 8);
    const body = buf.subarray(at + 8, at + 8 + length);
    if (type === 'IHDR') {
      width = body.readUInt32BE(0);
      height = body.readUInt32BE(4);
      const depth = body[8];
      const colour = body[9];
      if (depth !== 8 || (colour !== 2 && colour !== 6) || body[12] !== 0) throw new Error(`unsupported PNG (depth ${depth}, colour type ${colour}, interlace ${body[12]})`);
      channels = colour === 2 ? 3 : 4;
    } else if (type === 'IDAT') parts.push(body);
    else if (type === 'IEND') break;
    at += 12 + length;
  }
  const raw = zlib.inflateSync(Buffer.concat(parts));
  const stride = width * channels;
  const data = Buffer.alloc(stride * height);
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const src = y * (stride + 1) + 1;
    const dst = y * stride;
    for (let i = 0; i < stride; i++) {
      const left = i >= channels ? data[dst + i - channels] : 0;
      const up = y > 0 ? data[dst + i - stride] : 0;
      const corner = y > 0 && i >= channels ? data[dst + i - stride - channels] : 0;
      const x = raw[src + i];
      data[dst + i] = (filter === 0 ? x : filter === 1 ? x + left : filter === 2 ? x + up : filter === 3 ? x + ((left + up) >> 1) : x + paeth(left, up, corner)) & 0xff;
    }
  }
  return { width, height, channels, data };
}

function chunk(type, body) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(body.length, 0);
  head.write(type, 4, 'latin1');
  const tail = Buffer.alloc(4);
  tail.writeUInt32BE(crc32(head.subarray(4), body), 0);
  return Buffer.concat([head, body, tail]);
}

/** Writes an image as a PNG: per row the filter with the smallest residue, then deflate at level 9. */
function encode({ width, height, channels, data }) {
  const stride = width * channels;
  const out = Buffer.alloc((stride + 1) * height);
  const tries = [0, 1, 2, 3, 4].map(() => Buffer.alloc(stride));
  for (let y = 0; y < height; y++) {
    const row = y * stride;
    let best = 0;
    let bestCost = Infinity;
    for (let f = 0; f < 5; f++) {
      const t = tries[f];
      let cost = 0;
      for (let i = 0; i < stride; i++) {
        const x = data[row + i];
        const left = i >= channels ? data[row + i - channels] : 0;
        const up = y > 0 ? data[row + i - stride] : 0;
        const corner = y > 0 && i >= channels ? data[row + i - stride - channels] : 0;
        const v = (f === 0 ? x : f === 1 ? x - left : f === 2 ? x - up : f === 3 ? x - ((left + up) >> 1) : x - paeth(left, up, corner)) & 0xff;
        t[i] = v;
        cost += v < 128 ? v : 256 - v;
      }
      if (cost < bestCost) {
        bestCost = cost;
        best = f;
      }
    }
    out[y * (stride + 1)] = best;
    tries[best].copy(out, y * (stride + 1) + 1);
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = channels === 3 ? 2 : 6;
  return Buffer.concat([SIGNATURE, chunk('IHDR', header), chunk('IDAT', zlib.deflateSync(out, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

/**
 * Rewrites a PNG file with every colour channel rounded to `levels` evenly spaced values (alpha is
 * dropped: a screenshot has none). Returns {before, after} in bytes.
 */
function reduceLevels(file, levels) {
  const before = fs.statSync(file).size;
  const image = decode(file);
  const table = new Uint8Array(256);
  for (let v = 0; v < 256; v++) table[v] = Math.round((Math.round((v * (levels - 1)) / 255) * 255) / (levels - 1));
  const pixels = image.width * image.height;
  const rgb = Buffer.alloc(pixels * 3);
  for (let p = 0; p < pixels; p++) {
    rgb[p * 3] = table[image.data[p * image.channels]];
    rgb[p * 3 + 1] = table[image.data[p * image.channels + 1]];
    rgb[p * 3 + 2] = table[image.data[p * image.channels + 2]];
  }
  const png = encode({ width: image.width, height: image.height, channels: 3, data: rgb });
  fs.writeFileSync(file, png);
  return { before, after: png.length };
}

module.exports = { decode, encode, reduceLevels };
