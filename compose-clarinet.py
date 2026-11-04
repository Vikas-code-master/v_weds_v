"""Original baraat-band style piece: clarinet lead (Raag Khamaj) + dhol chaal
+ tuba oom-pah + tasha rolls + chimta. Renders a seamless loop as WAV."""
import sys, wave
import numpy as np

SR = 44100
BPM = 108
Q = 60 / BPM                      # quarter note (s)
BAR = 4 * Q
BARS = 28
N = int(BARS * BAR * SR)
TAIL = int(4 * SR)
rng = np.random.default_rng(11)

SA = 392.0                        # Sa = G4
def hz(semi, octave=0):
    return SA * 2 ** (semi / 12 + octave)

def buf():
    return np.zeros(N + TAIL)

def place(dst, src, t):
    i = int(t * SR)
    if i >= len(dst): return
    j = min(len(dst), i + len(src))
    dst[i:j] += src[: j - i]

# ---------------- melody (Khamaj: S R G m P D n S') ----------------
S, R, G, m, P, D, n = 0, 2, 4, 5, 7, 9, 10
S2, R2, G2, m2 = 12, 14, 16, 17
_ = None
A = [
    [(P, 1), (D, .5), (n, .5), (S2, 1), (n, .5), (D, .5)],
    [(P, 1.5), (m, .5), (G, 2)],
    [(G, .5), (m, .5), (P, .5), (D, .5), (P, 1), (m, .5), (G, .5)],
    [(R, 1), (G, .5), (R, .5), (S, 2)],
    [(S, .5), (R, .5), (G, .5), (m, .5), (P, 1), (P, 1)],
    [(D, .5), (P, .5), (m, .5), (G, .5), (m, 2)],
    [(G, .5), (m, .5), (P, .5), (D, .5), (n, .5), (D, .5), (P, .5), (m, .5)],
    [(G, 1), (R, 1), (S, 2)],
]
B = [
    [(S2, 1.5), (R2, .5), (G2, 1), (R2, .5), (S2, .5)],
    [(n, 1), (D, .5), (n, .5), (S2, 2)],
    [(P, .5), (D, .5), (n, .5), (S2, .5), (R2, 1), (S2, .5), (n, .5)],
    [(D, 1), (P, 1), (D, 2)],
    [(S2, 1.5), (R2, .5), (G2, 1), (m2, .5), (G2, .5)],
    [(R2, 1), (S2, .5), (n, .5), (S2, 2)],
    [(n, .5), (D, .5), (P, .5), (m, .5), (G, .5), (m, .5), (P, 1)],
    [(D, 1), (n, .5), (D, .5), (P, 2)],
]
A2 = A[:7] + [[(G, .5), (R, .5), (S, .5), (-2, .5), (S, 2)]]
END = [
    [(S2, 1), (n, .5), (D, .5), (P, 1), (m, .5), (G, .5)],
    [(S, 3), (_, 1)],
]
song = [A, B, A2, END]
roots = [S, S, S, S, S, m, S, S] + [S, S, S, m, S, S, S, P - 12] + [S, S, S, S, S, m, S, S] + [S, S]

notes, beat = [], 2 * 4            # melody enters after 2 intro bars
for section in song:
    for bar in section:
        for semi, d in bar:
            notes.append((beat, d, semi)); beat += d

# ---------------- clarinet synthesis ----------------
total = N + TAIL
freq = np.full(total, SA); env = np.zeros(total)
prev = None
for k, (start, d, semi) in enumerate(notes):
    t0 = start * Q
    i0, i1 = int(t0 * SR), int((start + d) * Q * SR)
    if semi is None:
        prev = None; continue
    f = hz(semi)
    seg = np.full(i1 - i0, f)
    L = i1 - i0
    t = np.arange(L) / SR
    # kan (grace note from the scale step above) on longer notes
    if d >= 1 and k % 2 == 0:
        g = int(0.055 * SR)
        seg[:g] = f * 2 ** (2 / 12)
    elif prev is not None:                         # quick slur from the previous note
        g = min(int(0.03 * SR), L)
        seg[:g] = np.geomspace(prev, f, g)
    depth = 0.005 * np.clip((t - 0.12) / 0.2, 0, 1)
    seg *= 1 + depth * np.sin(2 * np.pi * 5.8 * t)
    freq[i0:i1] = seg
    a = np.minimum(1, t / 0.022) * np.clip((t[-1] - t) / 0.035, 0, 1) ** .5
    a *= 0.92 + 0.08 * np.sin(2 * np.pi * 0.7 * t)  # breath swell
    if d >= 2:
        a *= 1 - 0.25 * (t / t[-1]) ** 2
    if start >= (BARS - 1) * 4:                     # final note fades
        a *= np.clip(1 - t / (d * Q), 0, 1)
    env[i0:i1] = np.maximum(env[i0:i1], a)
    prev = f
env = np.convolve(env, np.ones(220) / 220, mode="same")

phase = 2 * np.pi * np.cumsum(freq) / SR
clar = np.zeros(total)
for h in range(1, 14):
    if hz(0) * h > 11000: break
    amp = (1 / h ** 0.85) if h % 2 else (0.12 / h)
    clar += amp * np.sin(h * phase)
reed = rng.normal(0, 1, total)
reed -= np.convolve(reed, np.ones(4) / 4, mode="same")
clar = (clar + 0.05 * reed) * env * 0.2

# ---------------- dhol ----------------
def dagga(vel):                   # bass head
    t = np.arange(int(0.5 * SR)) / SR
    f = 70 + 90 * np.exp(-t / 0.025)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2)
    slap = rng.normal(0, 1, len(t)) * np.exp(-t / 0.006) * 0.3
    return vel * (body + slap)

def tilli(vel):                   # stick on treble head
    t = np.arange(int(0.12 * SR)) / SR
    crack = rng.normal(0, 1, len(t))
    crack -= np.convolve(crack, np.ones(3) / 3, mode="same")
    tone = np.sin(2 * np.pi * 640 * t)
    return vel * (0.9 * crack + 0.5 * tone) * np.exp(-t / 0.022)

dhol = buf()
E = Q / 2
chaal = {0: [("d", 1.0)], 2: [("t", .7)], 3: [("t", .55)], 4: [("d", .85), ("t", .3)],
         5: [("t", .35)], 6: [("t", .75)], 7: [("t", .45)]}
for bar in range(BARS):
    for e in range(8):
        for kind, vel in chaal.get(e, []):
            if bar == BARS - 1 and e >= 4: continue
            place(dhol, dagga(vel) if kind == "d" else tilli(vel), bar * BAR + e * E)
    if bar % 2 == 1 and bar < BARS - 2:          # extra bass push on bar ends
        place(dhol, dagga(.6), bar * BAR + 7 * E)
dhol *= 0.32

# ---------------- tasha rolls ----------------
tasha = buf()
def snare(vel):
    t = np.arange(int(0.09 * SR)) / SR
    x = rng.normal(0, 1, len(t))
    x -= np.convolve(x, np.ones(2) / 2, mode="same")
    return vel * x * np.exp(-t / 0.03)
for bar in (1, 9, 17, 25, 26):
    for s in range(8, 16):                        # 16th roll on the 2nd half of the bar
        place(tasha, snare(0.25 + 0.06 * (s - 8)), bar * BAR + s * Q / 4)
tasha *= 0.18

# ---------------- chimta / jingles on off-beats ----------------
chimta = buf()
def jingle(vel):
    t = np.arange(int(0.07 * SR)) / SR
    x = rng.normal(0, 1, len(t))
    x -= np.convolve(x, np.ones(2) / 2, mode="same")
    ring = sum(np.sin(2 * np.pi * fr * t) for fr in (4200, 5600, 7300)) / 3
    return vel * (0.5 * x + 0.5 * ring) * np.exp(-t / 0.018)
for bar in range(2, BARS - 1):
    for b in range(4):
        place(chimta, jingle(.5), bar * BAR + b * Q + E)
chimta *= 0.06

# ---------------- tuba oom-pah ----------------
def tuba(f, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t) + .45 * np.sin(4 * np.pi * f * t) + .2 * np.sin(6 * np.pi * f * t)
    return s * np.minimum(1, t / 0.015) * np.exp(-t / 0.22)
bass = buf()
for bi, r in enumerate(roots):
    bar = bi + 2
    root = hz(r, -2)
    fifth = root * 1.5
    for b, f in enumerate([root, fifth / 2 * 1, root, fifth / 2]):
        place(bass, tuba(f, Q * .9), bar * BAR + b * Q)
bass *= 0.11

# ---------------- mix, reverb, loop ----------------
dry_c = clar
dry_r = dhol + tasha + chimta + bass

def reverb_ir(seed, decay=.45):
    r = np.random.default_rng(seed)
    t = np.arange(int(1.8 * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t / decay)
    ir = np.convolve(ir, np.ones(8) / 8, mode="same")
    ir[: int(0.015 * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2))

def fft_conv(x, h):
    n = 1 << int(np.ceil(np.log2(len(x) + len(h))))
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[: len(x)]

mix = dry_c + dry_r
L = mix + 0.24 * fft_conv(dry_c, reverb_ir(1)) + 0.1 * fft_conv(dry_r, reverb_ir(3, .3))
Rr = mix + 0.24 * fft_conv(dry_c, reverb_ir(2)) + 0.1 * fft_conv(dry_r, reverb_ir(4, .3))
L += 0.08 * chimta - 0.04 * tasha
Rr += 0.08 * tasha - 0.04 * chimta

out = np.stack([L, Rr], axis=1)
out[:TAIL] += out[N:N + TAIL]
out = out[:N]
out = np.tanh(out / np.max(np.abs(out)) * 1.3) / np.tanh(1.3) * 0.89

with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype("<i2").tobytes())
print("wrote", sys.argv[1], round(N / SR, 1), "s")
