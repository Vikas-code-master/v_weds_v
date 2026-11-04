"""Original wedding instrumental: tanpura drone + bansuri melody in Raag Bhupali
+ soft dholak (keherwa) + temple bells. Renders a seamless 64 s loop as WAV."""
import sys, wave
import numpy as np

SR = 44100
BEAT = 0.8                      # 75 bpm
CYCLE = 8                       # keherwa: 8 beats
BEATS = 80                      # 10 cycles = 64 s
N = int(BEATS * BEAT * SR)
TAIL = int(5 * SR)
rng = np.random.default_rng(7)

SA = 293.66                     # Sa = D4; flute plays an octave up
def hz(semi, octave=0):
    return SA * 2 ** (semi / 12 + octave)

def buf():
    return np.zeros(N + TAIL)

# ---------------- tanpura drone ----------------
def tanpura_pluck(f, dur=4.2):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for k in range(1, 22):
        amp = 1 / k ** 0.85
        decay = np.exp(-t / (3.2 / (1 + 0.06 * k)))
        swell = 1 - np.exp(-t * (0.6 + k / 5))          # jawari: upper partials bloom
        det = 1 + rng.normal(0, 0.0004)
        s += amp * decay * swell * np.sin(2 * np.pi * f * k * det * t + rng.uniform(0, 6.28))
    return s * np.minimum(1, t / 0.01)

drone = buf()
pattern = [hz(-5, -1), hz(0), hz(0), hz(0, -1)]       # Pa, Sa, Sa, low Sa
plucks = {f: tanpura_pluck(f) for f in set(pattern)}
for b in range(BEATS + 4):
    f = pattern[b % 4]
    i = int(b * BEAT * SR)
    p = plucks[f]
    j = min(len(drone), i + len(p))
    if i < len(drone):
        drone[i:j] += p[: j - i] * (0.9 if f < 100 else 1.0)
drone *= 0.055

# ---------------- bansuri melody (Bhupali: S R G P D) ----------------
R = None
phrases = [
    [(4, 1), (2, 1), (0, 2), (-3, 1), (0, 1), (2, 1), (4, 1)],
    [(7, 2), (4, 1), (2, 1), (4, 3), (R, 1)],
    [(4, 1), (7, 1), (9, 2), (12, 1), (9, 1), (7, 2)],
    [(9, 1), (7, 1), (4, 1), (2, 1), (4, 2), (2, 1), (0, 1)],
    [(0, 1), (2, 1), (4, 1), (7, 1), (9, 1), (12, 3)],
    [(14, 1), (12, 1), (9, 1), (7, 1), (9, 2), (7, 2)],
    [(4, 1), (7, 1), (4, 1), (2, 1), (0, 2), (-3, 1), (-5, 1)],
    [(0, 6), (R, 2)],
]
notes, beat = [], 2 * CYCLE                         # melody enters after 2 cycles
for ph in phrases:
    for semi, d in ph:
        notes.append((beat, d, semi)); beat += d

freq = np.zeros(N + TAIL); env = np.zeros(N + TAIL)
glide = int(0.07 * SR)
prev_f = None
for start, d, semi in notes:
    i0, i1 = int(start * BEAT * SR), int((start + d) * BEAT * SR)
    if semi is None:
        prev_f = None
        continue
    f = hz(semi, 1)
    seg = np.full(i1 - i0, f)
    if prev_f:                                        # meend: glide from previous note
        g = min(glide, len(seg))
        seg[:g] = np.geomspace(prev_f, f, g)
    t = np.arange(i1 - i0) / SR
    vib_depth = 0.006 * np.clip((t - 0.35) / 0.4, 0, 1)
    seg *= 1 + vib_depth * np.sin(2 * np.pi * 5.2 * t)
    freq[i0:i1] = seg
    a = np.minimum(1, t / 0.06) * (0.85 + 0.15 * np.exp(-t / 0.25))
    rel = np.clip((t[-1] - t) / 0.06, 0, 1)            # tiny re-articulation dip
    a *= 0.75 + 0.25 * rel
    if d >= 3:
        a *= np.clip(1 - (t / (d * BEAT)) ** 3 * 0.5, 0, 1)
    env[i0:i1] = a
    prev_f = f
# smooth envelope edges and gaps
k = np.ones(int(0.02 * SR)) / int(0.02 * SR)
env = np.convolve(env, k, mode="same")
freq[freq == 0] = SA * 2
phase = 2 * np.pi * np.cumsum(freq) / SR
flute = np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase) + 0.04 * np.sin(4 * phase)
breath = rng.normal(0, 1, len(flute))
breath = breath - np.convolve(breath, np.ones(6) / 6, mode="same")   # crude high-pass
flute = (flute + 0.08 * breath) * env * 0.16

# ---------------- dholak (keherwa) ----------------
def bass_hit(vel):
    t = np.arange(int(0.45 * SR)) / SR
    f = 62 + 70 * np.exp(-t / 0.03)
    return vel * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)

def tre_hit(vel, f0=420):
    t = np.arange(int(0.18 * SR)) / SR
    tone = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.05)
    click = rng.normal(0, 1, len(t)) * np.exp(-t / 0.008)
    return vel * (0.8 * tone + 0.35 * click)

drums = buf()
kher = {0: ("b", 1.0), 1: ("b", .55), 2: ("t", .6), 3: ("t", .45), 4: ("t", .55),
        5: ("t", .4), 6: ("b", .8), 7: ("t", .5)}
for b in range(CYCLE, BEATS):                         # enters on cycle 2
    kind, vel = kher[b % CYCLE]
    if b >= BEATS - 2:
        vel *= 0.5
    i = int(b * BEAT * SR)
    h = bass_hit(vel) if kind == "b" else tre_hit(vel, 420 if b % 2 else 470)
    drums[i:i + len(h)] += h
    if b % CYCLE in (2, 5):                           # light off-beat ghost note
        j = i + int(BEAT / 2 * SR)
        g = tre_hit(0.22, 520)
        drums[j:j + len(g)] += g
drums *= 0.2

# ---------------- temple bells ----------------
def bell(f0, vel):
    t = np.arange(int(4 * SR)) / SR
    s = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1, 1.6), (2.0, .45, 1.1), (2.76, .5, .9), (5.4, .25, .5), (8.9, .12, .3)]:
        s += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-t / dec)
    return vel * s * np.minimum(1, t / 0.002)

bells = buf()
for c in range(0, BEATS // CYCLE, 2):
    i = int(c * CYCLE * BEAT * SR)
    h = bell(hz(0, 2), 1.0)
    bells[i:i + len(h)] += h
    j = i + int(0.35 * SR)
    h2 = bell(hz(7, 1), 0.5)
    bells[j:j + len(h2)] += h2
bells *= 0.03

# ---------------- mix, reverb, loop ----------------
dry = drone + flute + drums + bells

def reverb_ir(seed):
    r = np.random.default_rng(seed)
    t = np.arange(int(2.2 * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t / 0.55)
    ir = np.convolve(ir, np.ones(8) / 8, mode="same")  # darken
    ir[: int(0.012 * SR)] = 0                          # pre-delay
    return ir / np.sqrt(np.sum(ir ** 2))

def fft_conv(x, h):
    n = 1 << int(np.ceil(np.log2(len(x) + len(h))))
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[: len(x)]

wet_l = fft_conv(dry, reverb_ir(1))
wet_r = fft_conv(dry, reverb_ir(2))
L = dry + 0.32 * wet_l
Rch = dry + 0.32 * wet_r
# slight stereo placement: drone a bit left, bells a bit right
L += 0.15 * drone - 0.1 * bells
Rch += -0.05 * drone + 0.15 * bells

out = np.stack([L, Rch], axis=1)
out[:TAIL] += out[N:N + TAIL]                        # wrap the tail -> seamless loop
out = out[:N]
out = np.tanh(out / np.max(np.abs(out)) * 1.2) / np.tanh(1.2) * 0.89

path = sys.argv[1]
with wave.open(path, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype("<i2").tobytes())
print("wrote", path, round(N / SR, 1), "s")
