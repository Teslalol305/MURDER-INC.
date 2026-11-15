// Stub audio (CONTRACT 6.9): silence with the full API. Also what `?noaudio=1` selects.

export function createAudio() {
  const noop = () => {};
  const loopHandle = { setPos: noop, setVolume: noop, stop: noop };

  return {
    unlock: noop,
    setVolume: noop,
    setPaused: noop,
    setInterior: noop,
    setMusicIntensity: noop,
    play: () => null,
    loop: () => loopHandle,
    sting: noop,
    update: noop,
  };
}
