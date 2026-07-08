export const SAMPLE_RATE = 16000;
export const CHUNK_SAMPLES = Math.floor((SAMPLE_RATE * 320) / 1000);

export function rmsEnergy(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i += 1) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

export function resampleLinear(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    const src = i * ratio;
    const idx = Math.floor(src);
    const frac = src - idx;
    const a = input[idx] ?? 0;
    const b = input[idx + 1] ?? a;
    out[i] = a + (b - a) * frac;
  }
  return out;
}

export function playSpeechSynthesisFallback(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      resolve();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text.replace(/\.\.\./g, ","));
    utter.rate = 1.05;
    utter.onend = () => resolve();
    utter.onerror = () => resolve();
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  });
}

export async function startMicCapture(onChunk: (pcm: Float32Array) => void) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  let carry = new Float32Array(0);

  processor.onaudioprocess = (ev) => {
    const pcm16 = resampleLinear(ev.inputBuffer.getChannelData(0).slice(), ctx.sampleRate, SAMPLE_RATE);
    const merged = new Float32Array(carry.length + pcm16.length);
    merged.set(carry, 0);
    merged.set(pcm16, carry.length);
    let offset = 0;
    while (offset + CHUNK_SAMPLES <= merged.length) {
      onChunk(merged.subarray(offset, offset + CHUNK_SAMPLES));
      offset += CHUNK_SAMPLES;
    }
    carry = merged.subarray(offset);
  };

  source.connect(processor);
  processor.connect(ctx.destination);

  return () => {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
    carry = new Float32Array(0);
  };
}