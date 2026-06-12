# Passive RF Maritime Domain Awareness — Deep Technical Research
### A founder's reference: academic literature, competitive landscape, implementation science

---

## Executive Summary

This document synthesises the technical, academic, and competitive landscape for building a ground-based passive RF sensor network for maritime domain awareness (MDA). The core premise: many operational vessels emit radio-frequency metadata — AIS transponders, VHF radios, marine radar or satellite communications — and those emissions can sometimes be passively received, timestamped, geolocated via time-difference of arrival (TDOA), and analysed to cue investigation when a vessel goes "dark" by switching off or spoofing AIS.

The sovereign Australian angle: the market leaders (Hawkeye 360, Unseenlabs) are space-based and US/French respectively. There is no obvious Australian category leader publicly positioned around ground-based passive RF geolocation of maritime emitters for northern choke points. The target customers (AFMA, Australian Border Force, ADF-adjacent users) already value multi-source maritime surveillance. Funding should be modelled conservatively: RDTI may support eligible experimental R&D after registration and tax timing; DIDG should be treated as later capability uplift/security/skilling/equipment support, not core product R&D or prototyping; ASCA/customer pilots are upside, not guaranteed cash.

---

## Part 1: The Problem Space

### 1.1 Why AIS Alone Fails

The Automatic Identification System (AIS) is mandated under SOLAS for all international vessels over 300 gross tonnes, cargo vessels over 500 tonnes, and all passenger ships. AIS transponders broadcast vessel identity, position, speed, and heading every 2–10 seconds on 161.9625 MHz (AIS 1) and 162.0125 MHz (AIS 2).

**The fundamental weakness:** AIS is cooperative. Vessels can simply turn it off.

Dark vessel behaviour falls into three categories:
1. **Intentional disabling** — vessel switches off AIS to avoid detection during illicit activity (IUU fishing, sanctions evasion, drug or people smuggling)
2. **AIS spoofing** — vessel broadcasts false identity, position, speed, or heading while continuing to transmit
3. **Below-threshold vessels** — fishing vessels under 300 tonnes are not required to carry AIS

**Academic evidence on spoofing:** A 2025 study analysing AIS data from the Black Sea found ML models could detect spoofed tracks with accuracy exceeding 98% — but only when RF ground truth was available for comparison. Without an independent position fix, spoofed AIS is undetectable from AIS data alone. *(Detection of spoofed AIS: Simulated tracks vs. real maritime data, ResearchGate, 2025)*

**The scale of the problem in Australia's waters:** AFMA's Operation Jawline intercepted over 100 IUU vessels in a single season. These vessels were detected via patrol assets — expensive, slow, and geographically limited. Persistent RF-based detection would cue patrol assets rather than requiring blanket coverage.

### 1.2 The RF Emissions a Dark Vessel Cannot Hide

Even with AIS disabled, a working vessel emits RF across several bands:

| Emission type | Frequency | Range | Notes |
|---|---|---|---|
| AIS (when active) | 161.975 / 162.025 MHz | ~40 nmi | Primary tracking signal |
| Marine VHF radio | 156–174 MHz | ~25 nmi | Channel 16 (distress) always monitored |
| Marine radar (X-band) | 9.2–9.5 GHz | Detectable at distance | Rotating, distinctive pulse pattern |
| Marine radar (S-band) | 2.9–3.1 GHz | Detectable at distance | Larger vessels |
| EPIRB / SART | 406 MHz / 9.2 GHz | Global | Emergency beacons |
| Satellite phones | 1.6 GHz (Iridium), 1.5 GHz (Thuraya) | Depends on link | High-value target for intelligence |
| GNSS receiver noise | ~1.575 GHz | Short range | Very low power, difficult to detect |

A vessel intent on reducing detectability can reduce emissions, so RF detection is not guaranteed. The operational thesis is narrower: enough vessels leak enough RF metadata often enough to create valuable detection and cueing opportunities. Radar is required for safe navigation. VHF is required for distress monitoring. These emissions are the persistent signals this platform detects.

---

## Part 2: TDOA Geolocation — The Physics and Maths

### 2.1 The Core Concept

Time Difference of Arrival (TDOA) geolocation works on a simple geometric principle: if the same signal arrives at receiver A before receiver B, the emitter must be closer to A than B. The locus of all points equidistant from the difference (dA − dB = constant × c, where c is the speed of light) describes a **hyperbola** in 2D, or a **hyperboloid** in 3D.

With:
- **2 receivers** → 1 hyperbola → a line of possible positions (ambiguous)
- **3 receivers** → 2 hyperbolas → 1 intersection point (determined)
- **4+ receivers** → overdetermined system → least-squares solution with uncertainty quantification

The speed of light is ~3 × 10⁸ m/s. A 1-microsecond timing error translates to a 300-metre position error. At inter-site baselines of 100–500 km (typical for northern Australian nodes), positional accuracy of 1–5 km is achievable with nanosecond timing.

### 2.2 The Timing Problem and Its Solution

**Why timing is hard:** Two RTL-SDR receivers plugged into separate computers will drift apart in time — even if synchronised at startup. A standard PC clock drifts by microseconds per second. This is catastrophic for TDOA.

**The solution: GPS-disciplined oscillators (GPSDOs)**

A GPSDO combines a GPS receiver with a high-stability oscillator (quartz or rubidium). The GPS 1-pulse-per-second (1PPS) signal is used as a phase-locked loop reference, disciplining the local oscillator to GPS time (which is accurate to ~20 nanoseconds globally). With a GPSDO, all receivers share a common time reference regardless of geographic separation.

**Practical implementations:**
- **KiwiSDR** (~$300): HF SDR (0–30 MHz) with built-in GPS input. Already implements TDOA via the public KiwiSDR network. GPS synchronises clocks worldwide. The publicly available KiwiSDR TDOA network demonstrated sub-kilometre accuracy for HF emitter localisation. Not suitable for VHF/AIS (wrong frequency range) but the timing architecture is the reference implementation to study.
- **Leo Bodnar GPSDO** (~$180): Provides 10 MHz and 1PPS reference signals for any SDR. Used in the research literature for sub-nanosecond synchronisation when paired with premium SDRs.
- **RTL-SDR v4 + external GPSDO**: The low-cost approach. RTL-SDR v4 has an external clock input; feeding it a GPSDO-derived 10 MHz reference achieves <100 ns synchronisation. A Czech master's thesis (Jan Hrach, Univerzita Karlova) demonstrated functional TDOA multilateration using unmodified RTL-SDRs with known-location transmitters as timing references — a viable bootstrap technique.

**Academic benchmark:** A UAV emitter localisation testbed published on arXiv (2022) used Stanford Research Systems FS740 GPSDOs and achieved 0.482 ns² timing variance after GNSS post-processing correction — translating to <15 cm ranging error at close range. Production maritime systems work at much longer ranges and accept proportionally larger position uncertainty, typically 1–5 km at 200 km baseline.

### 2.3 The GCC-PHAT Algorithm — The Signal Processing Core

The TDOA estimate itself comes from computing when the same signal arrives at each receiver. The standard algorithm is **Generalised Cross-Correlation with Phase Transform (GCC-PHAT)**, published by Knapp and Carter in 1976 (IEEE Transactions on Acoustics, Speech and Signal Processing, Vol. ASSP-24(4), pp. 320–327) and still the standard 50 years later.

**What it does:** Given two signals x_i(t) and x_j(t) from two receivers, the GCC-PHAT cross-correlation function is:

```
R_PHAT(τ) = ∫ [X_i(ω) · X_j*(ω)] / [|X_i(ω)| · |X_j(ω)|] · e^(jωτ) dω
```

The denominator normalises the spectral density (the "phase transform"), whitening the signals so the cross-correlation peak is sharper and more robust to noise and multipath. The lag τ at the peak of R_PHAT is the TDOA estimate.

**Why it matters for this application:** Marine environments are noisy. Multi-path reflections from sea surface, coastal topography, and near-field interference degrade simple cross-correlation. GCC-PHAT is specifically robust to these conditions, which is why it has been adopted in every serious TDOA maritime geolocation system.

**Implementation note:** In Python, this is ~20 lines of code using `numpy.fft`. The compute-intensive part is running it continuously on streaming IQ data, which requires efficient buffer management. A Raspberry Pi 5 can handle this in real time for a single signal; a modest x86 edge node handles multiple frequency bands.

### 2.4 Hyperbolic Positioning — From TDOA to Map Coordinates

Given three TDOA measurements (τ_12, τ_13, τ_23 from receiver pairs 1-2, 1-3, 2-3), the emitter position (x, y) satisfies:

```
√((x-x₁)² + (y-y₁)²) - √((x-x₂)² + (y-y₂)²) = c · τ₁₂
√((x-x₁)² + (y-y₁)²) - √((x-x₃)² + (y-y₃)²) = c · τ₁₃
```

This is a nonlinear system. Two solution approaches:

1. **Bancroft / Chan algorithm:** Closed-form algebraic solution. Fast. Works well when noise is low and geometry is good. Derived from GPS satellite positioning mathematics.

2. **Iterative least-squares / Gauss-Newton:** Minimises residuals iteratively. More robust to noise and geometry. Naturally produces uncertainty ellipses (the actuarial interpretation: the 95% confidence region around the position estimate). This is where your actuarial background is directly applicable — you're fitting a nonlinear model to noisy observations and characterising the posterior uncertainty.

**For maritime applications:** The European Commission Joint Research Centre (JRC) published "Multi-Network Asynchronous TDOA Algorithm Test in a Simulated Maritime Scenario" (Sensors, 2020, DOI: 10.3390/s20071842), which extends classical TDOA to handle asynchronous receivers (different network timing standards) — directly relevant to the challenge of integrating heterogeneous nodes across Australia's northern approaches.

### 2.5 FDOA — The Velocity Dimension

Frequency Difference of Arrival (FDOA) is the complementary technique to TDOA. Moving emitters exhibit a Doppler shift; two receivers at different positions see different Doppler shifts, and the difference localises the emitter's velocity vector. Combined TDOA+FDOA (from the IEEE paper "Geolocation using TDOA and FDOA measurements" by Musicki and Koch) can geolocate and track moving emitters from a single snapshot, with accuracy near the Cramér-Rao lower bound.

For maritime applications: AIS-transmitting vessels are typically moving at 5–15 knots (2.5–7.5 m/s). At 162 MHz, the Doppler shift is tiny (~1 Hz) and generally below the frequency resolution of commodity SDRs. FDOA is more useful at higher frequencies (radar bands) or for aircraft (ADS-B). Include it as Phase 2 capability.

---

## Part 3: RF Fingerprinting — Vessel Identity Beyond AIS

### 3.1 The Concept

Every RF transmitter has hardware imperfections — tolerances in oscillator frequency, transistor characteristics, amplifier nonlinearities — that create a unique "fingerprint" in the emitted signal. This fingerprint is independent of the transmitted content and persists over time. It's the RF equivalent of a handwriting sample.

**For maritime vessels:** A vessel's radio equipment has a fingerprint in its:
- Carrier frequency offset (CFO) — how far the oscillator drifts from nominal
- Phase noise — the spectral purity of the carrier
- I/Q imbalance — hardware imperfection in the SDR front-end creating spurious sidebands
- Turn-on transient — the first few milliseconds of a transmission have a characteristic shape
- Pulse repetition interval (for radar) — timing signature unique to each radar unit

### 3.2 Academic Literature

**Survey paper:** "A comprehensive survey on radio frequency (RF) fingerprinting: Traditional approaches, deep learning, and open challenges" (ScienceDirect, 2022) — the canonical reference. Covers feature extraction (CFO, phase noise, IQ imbalance, transients) and classification architectures (CNN, LSTM, transformer). Key finding: deep learning CNNs trained on raw IQ samples consistently outperform hand-crafted feature approaches, achieving >95% identification accuracy in controlled conditions.

**Wiley paper:** "Electromagnetic Signal Intelligent Identification Based on Radio Frequency Fingerprints" (2022) — describes the full pipeline: data acquisition → preprocessing → fingerprint extraction → classification. Notes that SDR hardware quality affects fingerprint consistency; higher-grade SDRs (HackRF, USRP) produce more stable fingerprints than RTL-SDR. Implication: RTL-SDR is fine for POC; production nodes will use better hardware.

**OrbID paper (2025):** "OrbID: Identifying Orbcomm Satellite RF Fingerprints" — applies RF fingerprinting to satellite communications. Collected 8.9 million samples from multiple SDRs. Demonstrates fingerprint stability over time — the same transmitter is identifiable weeks later. Also introduces privacy-preserving preprocessing. Directly relevant: your vessel fingerprints need to be stable over months and years.

**MDPI Electronics (2024):** "RF Fingerprinting Using Transient-Based Identification Signals at Sampling Rates Close to the Nyquist Limit" — shows that transient signals (the first 0.5–2ms of transmission) contain the richest fingerprint information and work at low sampling rates. Implication: even cheap RTL-SDR hardware captures the transient if configured correctly.

### 3.3 What to Fingerprint in Maritime Vessels

Priority targets ranked by RF signal strength and persistence:

1. **AIS transponder** — well-defined GMSK modulation at 162 MHz; hardware imperfections in oscillator create measurable CFO and phase noise signature. Best target for fingerprinting.
2. **VHF marine radio** — FM modulation; turn-on transients are highly characteristic. Vessels transmit regularly on Channel 16.
3. **Marine radar** — pulse timing and shape is equipment-specific. Requires faster sampling rate (>20 MHz) to capture X-band pulses; better suited to HackRF or USRP-class hardware.
4. **Satellite phone** — Iridium and Thuraya have measurable burst timing signatures.

### 3.4 The Pipeline in Practice

```
Raw IQ samples → Band filter → Burst detection → Transient extraction
→ Feature vector (CFO, phase noise, IQ imbalance, spectral kurtosis)
→ CNN classifier → Vessel identity probability distribution
→ Bayesian update of vessel track
```

Training data: collect 1,000+ transmissions from each vessel with known AIS identity. Extract feature vectors. Train CNN. At inference time, RF fingerprint + TDOA position estimate → identity + position fix, independent of what AIS claims.

---

## Part 4: AIS Anomaly Detection — The Intelligence Layer

### 4.1 The Taxonomy of Vessel Anomalies

Academic literature (Machine Learning-Assisted Anomaly Detection in Maritime Navigation Using AIS Data, arXiv:2002.05013) categorises vessel anomalies as:

1. **AIS on-off switching (OOS)** — vessel disappears from AIS and reappears; hidden Markov model (HMM) with channel characteristics detects deliberate vs. accidental gaps
2. **Position spoofing** — reported AIS position inconsistent with RF-derived TDOA position
3. **Speed anomalies** — reported speed physically impossible given time/distance
4. **Trajectory anomalies** — vessel deviates from expected route for vessel type / historical pattern
5. **Dark vessel** — RF emissions detected with no corresponding AIS broadcast
6. **Loitering** — vessel stationary or slow-moving in area inconsistent with vessel type (e.g. cargo vessel drifting over fishing ground)
7. **Rendezvous** — two vessels meet at sea with AIS disabled (classic IUU fishing mothership transfer or sanctions evasion)

### 4.2 ML Approaches — What the Literature Shows

**LSTM-based trajectory prediction (dominant approach, 2020–2025):**

Multiple papers converge on Bidirectional LSTM with encoder-decoder architecture as the best vessel track predictor. The 2024 ScienceDirect paper on Shanghai Port AIS data reported 92.7% anomaly detection accuracy using HybridAttn-BiRNN (a variant that combines temporal and feature attention).

The 2025 TANDFONLINE paper "Ship behavior prediction and anomaly detection using LSTM-DCross" introduces a deep cross network that integrates position, speed, and course simultaneously in a single model, outperforming models that treat them separately.

**The actuarial connection:** Anomaly detection via LSTM is fundamentally a likelihood problem: given historical track H and vessel type V, what is P(current observation | H, V)? Low probability = anomaly. This is exactly an actuarial credibility problem — you're assigning experience-based probability to observations given priors. The difference from classical actuarial work is that the "claims" are vessel positions and the "risk factors" are vessel type, route, time of day, weather.

**Bayesian approaches (your strongest fit):**

A Bayesian network approach (referenced in arXiv:2002.05013) handles missing values and provides explainable outputs — critical for government customers who need to justify intercept decisions. A Gaussian Mixture Model over vessel position/velocity state space provides:
- Prior distribution from historical vessel tracks
- Likelihood from new TDOA observation
- Posterior = updated position estimate with uncertainty ellipse

This is directly implementable in Python (scikit-learn GaussianMixture, scipy.stats) with your existing quantitative skills.

**The frontier: LLM-based analysis (2025):**

"AIS-LLM: A Unified Framework for Maritime Trajectory Prediction, Anomaly Detection, and Collision Risk Assessment" (arXiv:2508.07668, 2025) converts AIS data into natural language prompts fed to Qwen2-1.5B. This is exactly what your Claude analyst layer does — you're a year ahead of the academic curve in terms of what you've already built at NXT Bioscience.

### 4.3 The "Sea-cret Agents" Dark Vessel Reconstruction Paper

The most directly relevant recent paper: "Sea-cret Agents: Maritime Abduction for Region Generation to Expose Dark Vessel Trajectories" (arXiv:2502.01503, Feb 2025). The paper specifically addresses the problem of reconstructing a vessel's trajectory during an AIS-dark period — exactly the core product capability.

Their approach: use abductive reasoning to generate plausible regions where a dark vessel could have gone given physics constraints (maximum speed, turning radius) and contextual knowledge (known fishing grounds, port locations, shipping lanes). The output is a probability density over possible locations — a "where could it be?" map rather than a point estimate.

This is the intelligence product your AFMA customer actually wants. Not just "this vessel went dark," but "given that it went dark here and reappeared there, here are the five most probable routes it took and their associated likelihoods."

---

## Part 5: The Competitive Landscape

### 5.1 Space-Based RF (Direct Competitors, But Different Delivery)

**Hawkeye 360 (US)**
- Technology: Satellite clusters of 3 (each cluster = 1 TDOA solve). 144 MHz – 15 GHz coverage.
- Strengths: Global coverage; detects vessel radar, VHF, satellite comms
- Weaknesses: Revisit rate is hours (not continuous); latency of 15–30 min from collection to delivery; US company = ITAR considerations; expensive ($12.25M USN contract for one maritime data sharing program)
- Your angle: Zero latency (ground-based = real-time), continuous coverage in your AOI, sovereign, no ITAR

**Unseenlabs (France)**
- Technology: Single-satellite passes. Captures electromagnetic "fingerprint" of each emitter. ITAR-free (French).
- Strengths: RF fingerprinting is explicitly their core product; proprietary fingerprint database built over years of satellite passes
- Weaknesses: Single-satellite = revisit rate is hours; French-hosted infrastructure; European market focus
- Your angle: Northern Australia is not Unseenlabs' priority market. They have no persistent coverage of the Timor Sea or Torres Strait.

**Spire Global (US)**
- Technology: Multi-purpose nanosatellite constellation. AIS, weather, GNSS-RO, RF.
- Strengths: Huge constellation, low revisit rate
- Weaknesses: RF capability is not their primary focus; primarily sells AIS data; US company

**Key insight:** All three space-based players have the same fundamental weakness in your target geography — coverage is periodic (orbital mechanics), not persistent. A ground-based cluster can provide **persistent, low-latency** coverage inside selected instrumented choke points — a different coverage model to satellites, not a replacement for broad-area space-based RF. Latency: satellites are generally revisit/collection constrained; a ground cluster can support sub-minute alerting inside its instrumented area, subject to signal detection and processing.

### 5.2 Australian Competitors

**Arkeus (Melbourne)** — hyperspectral optical radar (HSOR) for UAVs and aircraft. Optical domain, not RF. Complementary technology, potential integration partner. Just raised $25M Series A. They are the "eyes" — you are the "ears."

**HEO (Sydney)** — non-Earth imaging from space, satellite-to-satellite optical imagery. Space domain awareness, not maritime RF. Different market.

**Myriota (Adelaide)** — IoT satellite connectivity. Provides low-power IoT messaging from remote assets. Could be used for backhaul from your remote sensor nodes (Cocos Islands, etc.) where terrestrial connectivity is unavailable.

**Saber Astronautics (Sydney)** — spacecraft operations, space domain awareness. Not maritime.

**The gap:** no obvious Australian category leader is publicly focused on ground-based passive RF geolocation for maritime choke-point validation. This is the potential white space.

### 5.3 International Non-Satellite Competitors

**Pole Star (UK)** — vessel tracking software. AIS aggregation and analytics. No RF geolocation.

**Windward (Israel)** — maritime AI platform. Multi-source fusion (AIS + SAR + EO + RF). Buys RF data from Hawkeye 360 and Unseenlabs. A potential **customer** or **data partner** rather than competitor — they need a persistent ground-based RF feed for the Indo-Pacific and have no sovereign reason to build it themselves.

**Global Fishing Watch** — NGO-based AIS analytics for IUU detection. No RF capability. Potential data-sharing partner for their AIS dataset (which would be your training data).

**Kpler / Vortexa** — commodity vessel tracking using AIS. Not RF.

---

## Part 6: Hardware Implementation

### 6.1 SDR Hardware Comparison

| Hardware | Cost | Freq range | Sample rate | ADC bits | Clock input | Notes |
|---|---|---|---|---|---|---|
| RTL-SDR v4 | ~$45 | 500 kHz–1.75 GHz | 3.2 MS/s | 8-bit | Yes (external) | POC hardware. Limited dynamic range. Adequate for AIS. |
| KiwiSDR | ~$300 | 0–30 MHz | 30.72 MS/s | 14-bit | GPS built-in | HF only. Not suitable for VHF/AIS directly. Gold standard for TDOA timing architecture. |
| Airspy Mini | ~$100 | 24–1800 MHz | 6 MS/s | 12-bit | No | Better than RTL-SDR. No external clock. |
| HackRF One | ~$340 | 1 MHz–6 GHz | 20 MS/s | 8-bit | Yes | Wide range. Low noise figure. Good for radar detection. |
| USRP B210 | ~$2,200 | 70 MHz–6 GHz | 56 MS/s | 12-bit | Yes (GPSDO) | Production-grade. What Hawkeye 360 terrestrial counterparts use. |
| LimeSDR Mini | ~$200 | 10 MHz–3.5 GHz | 40 MS/s | 12-bit | Yes | Good balance. Supported by SoapySDR. |

**Recommendation for each phase:**
- POC (months 1-6): RTL-SDR v4 × 2, Leo Bodnar GPSDO × 2 (~$500 total)
- Pilot node (months 6-18): LimeSDR Mini or HackRF + GPSDO (~$600–800/node)
- Production node: USRP B210 + Rubidium GPSDO (~$3,000–5,000/node)

### 6.2 Antenna Selection

For AIS (162 MHz) and marine VHF (156–174 MHz):
- **Discone antenna** — wideband, omni-directional, adequate gain (~3 dBi). Cheap (~$30). Good for POC.
- **Vertical collinear** (e.g., Shakespeare 5101) — purpose-built marine VHF antenna, higher gain (~6 dBi), longer range. What commercial AIS receivers use.
- **Yagi** (directional) — if you want to reject interference from a specific direction and maximise gain toward the ocean. 10+ dBi gain but loses omni-directionality.

For X-band radar (9.2–9.5 GHz): requires purpose-built microwave horn or patch antenna. Different build; Phase 2 only.

### 6.3 Edge Node Architecture

Each sensor node runs:
```
Antenna → LNA (low-noise amplifier) → SDR → Raspberry Pi 5 / x86 SBC
         → GNU Radio signal processing pipeline
         → AIS/ADS-B/VHF decoder
         → IQ timestamper (GPSD + PPS kernel driver)
         → MQTT publisher → encrypted VPN tunnel → central server
```

The GPSD + PPS combination is critical. The Linux kernel PPS driver locks onto the GPS 1-pulse-per-second signal and timestamps IQ samples to within 1 microsecond. At 300-km baselines, 1 µs = 300 m positional error — adequate for maritime surveillance.

---

## Part 7: Software Stack Deep Dive

### 7.1 Signal Processing Layer

**GNU Radio** (gnuradio.org): The open-source SDR framework. Python and C++ blocks connected in a flowgraph. Key blocks for this project:
- `rtlsdr_source` or `soapy_source`: hardware abstraction
- `low_pass_filter`: band isolation
- `rational_resampler`: sample rate conversion
- `quad_demod`: FM demodulation (for VHF voice)

**gr-ais** (github.com/bistromath/gr-ais): GNU Radio plugin for AIS decoding. Handles dual-channel (161.975 + 162.025 MHz) simultaneously. Outputs NMEA sentences. Well-maintained.

**pyais** (pip install pyais): Pure Python AIS decoder. Simpler than gr-ais. Parses NMEA to Python objects. Good for rapid prototyping; use gr-ais for production.

**rtl-ais** (github.com/dgiardini/rtl-ais): Standalone C program that accepts RTL-SDR input and outputs NMEA sentences. Runs in Docker. Lowest-friction way to start receiving AIS.

**pyModeS** (pip install pyModeS): Pure Python ADS-B (aircraft transponder) decoder. If you want to detect aircraft in addition to vessels, this handles it.

### 7.2 TDOA Engine (Your Core IP)

This is the component you write. ~500–800 lines of Python. Key functions:

```python
# 1. GCC-PHAT cross-correlation
import numpy as np

def gcc_phat(sig_i, sig_j, fs, max_tau=None):
    """
    Estimate TDOA between sig_i and sig_j using GCC-PHAT.
    Returns: tau (seconds), correlation function
    """
    n = sig_i.shape[0] + sig_j.shape[0]
    
    # FFT of both signals
    SIG_I = np.fft.rfft(sig_i, n=n)
    SIG_J = np.fft.rfft(sig_j, n=n)
    
    # Cross-power spectrum
    R = SIG_I * np.conj(SIG_J)
    
    # Phase transform (PHAT weighting)
    R_phat = R / (np.abs(R) + 1e-10)  # epsilon avoids div by zero
    
    # Inverse FFT → time-domain cross-correlation
    cc = np.fft.irfft(R_phat, n=n)
    max_shift = int(np.ceil(fs * max_tau)) if max_tau else n // 2
    cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))
    
    # Find peak
    tau = (np.argmax(np.abs(cc)) - max_shift) / fs
    return tau

# 2. Hyperbolic positioning (Chan algorithm)
from scipy.optimize import minimize

def tdoa_locate(receiver_positions, tdoa_measurements, c=3e8):
    """
    Given N receiver positions and (N-1) TDOA measurements,
    return estimated emitter position and uncertainty.
    
    receiver_positions: Nx2 array of (lat, lon) in metres (projected)
    tdoa_measurements: (N-1) array of time differences in seconds
    """
    range_diffs = tdoa_measurements * c  # convert to distance
    
    def residuals(pos):
        ranges = np.sqrt(np.sum((receiver_positions - pos)**2, axis=1))
        predicted_diffs = ranges[1:] - ranges[0]
        return np.sum((predicted_diffs - range_diffs)**2)
    
    # Initial guess: centroid of receivers
    x0 = np.mean(receiver_positions, axis=0)
    result = minimize(residuals, x0, method='Nelder-Mead')
    
    # Uncertainty: compute Jacobian for Cramér-Rao bound
    # ... (full uncertainty quantification adds ~100 lines)
    
    return result.x, result.fun  # position estimate, residual error
```

### 7.3 Data Pipeline

**Message broker: MQTT (Eclipse Mosquitto)**
Each sensor node publishes to topics:
- `vessel/ais/{mmsi}` — decoded AIS messages
- `sensor/{node_id}/iq_burst` — timestamped IQ burst (for TDOA)
- `sensor/{node_id}/status` — heartbeat, SNR, node health

Central server subscribes to all topics, processes in real time.

**Time-series database: TimescaleDB**
TimescaleDB (PostgreSQL extension) is the correct choice over InfluxDB for this application because:
1. You need to JOIN vessel tracks with risk profiles, port records, and AIS data — standard SQL JOINs work natively
2. TimescaleDB hypertables provide automatic time-partitioning with standard SQL interface
3. Your existing Python/pandas skills transfer directly (SQLAlchemy integration)
4. PROTECTED-level hosting on AUCloud supports PostgreSQL natively

Schema sketch:
```sql
-- Core tables
CREATE TABLE vessels (mmsi TEXT PRIMARY KEY, name TEXT, type INT, flag TEXT, ...);
CREATE TABLE ais_positions (time TIMESTAMPTZ, mmsi TEXT, lat FLOAT, lon FLOAT, 
    sog FLOAT, cog FLOAT, source TEXT);  -- hypertable on time
CREATE TABLE rf_detections (time TIMESTAMPTZ, node_id TEXT, frequency FLOAT,
    signal_strength FLOAT, fingerprint_vector BYTEA);  -- hypertable on time
CREATE TABLE tdoa_fixes (time TIMESTAMPTZ, lat FLOAT, lon FLOAT, 
    uncertainty_m FLOAT, contributing_nodes TEXT[]);  -- position fixes from TDOA
CREATE TABLE dark_vessel_events (id UUID, start_time TIMESTAMPTZ, 
    last_known_lat FLOAT, last_known_lon FLOAT, rf_detections_count INT,
    risk_score FLOAT, status TEXT);  -- the core intelligence product
```

### 7.4 The Anomaly Detection Model

Three-layer detection cascade (each layer feeds the next):

**Layer 1 — Rule-based pre-filter (fast, runs on every message):**
- AIS gap > 2 hours in known fishing ground? → Flag
- Reported speed > 30 knots for vessel type "fishing"? → Flag
- AIS position more than 50 km from TDOA-derived position? → Flag

**Layer 2 — Statistical model (medium, runs every 15 min):**
- Gaussian Mixture Model over (lat, lon, speed, heading, time-of-day) for each vessel type
- Mahalanobis distance of current observation from expected distribution
- If distance > threshold → Anomaly score
- Implemented: `sklearn.mixture.GaussianMixture`

**Layer 3 — LSTM trajectory predictor (slow, runs hourly on flagged vessels):**
- Trained on 6 months of AIS history for vessel type
- Predicts next 6-hour track
- If actual track deviates > 2 sigma from predicted → Elevated risk
- Architecture: Bi-LSTM with attention (following the 2024 ScienceDirect paper)
- Framework: PyTorch or Keras

**Output:** Risk score 0–100 with explainable feature contributions (gradient-based attribution, similar to SHAP values). AFMA operators need to justify intercept decisions in court — explainability is not optional.

### 7.5 Training Data Sources

| Source | Data | Cost | Notes |
|---|---|---|---|
| MarineTraffic API | Historical AIS, vessel database | $0–$500/mo | Free tier adequate for initial training |
| AISHub | Aggregated AIS from community receivers | Free | Register as contributor |
| Global Fishing Watch | Fishing vessel AIS + behaviour labels | Free API | Invaluable for IUU training labels |
| NOAA CoastWatch | Environmental/weather data | Free | Add as contextual features |
| spire.com | Historical AIS from satellites | Commercial | High coverage for remote areas |
| Your own nodes | Ground truth RF + AIS | Cost of nodes | The proprietary data moat |

---

## Part 8: Platform and Delivery

### 8.1 Sovereign Cloud Hosting

For PROTECTED-level classification (required for ADF customers):

**AUCloud** (aucloud.com.au): IRAP-assessed, PROTECTED-certified. Hosted in Canberra and Sydney. Supports Kubernetes, PostgreSQL/TimescaleDB, and standard Linux workloads. Pricing comparable to AWS. **Recommended choice** — purpose-built for Australian government sovereign requirements.

**Vault Cloud** (vaultcloud.com.au): Also PROTECTED-certified. Based in Canberra. Alternative if AUCloud capacity is constrained.

**AWS GovCloud:** US-hosted. Not sovereign. Inappropriate for PROTECTED data even though commonly used. Avoid.

### 8.2 Dashboard Stack

**Plotly Dash** (dash.plotly.com): Python-native reactive web framework. Build the entire dashboard in Python. Integrates with pandas, TimescaleDB. Mapbox GL JS integration for vessel track maps. Main limitation: not as fast as purpose-built React for real-time updates.

**Grafana + TimescaleDB**: Open-source dashboarding. Excellent for real-time telemetry monitoring (node health, signal levels). Less good for custom vessel intelligence workflows. Use for internal ops monitoring.

**Custom React + Deck.gl**: For the customer-facing intelligence dashboard. Deck.gl is Uber's open-source WebGL mapping library — handles 100,000+ vessel tracks smoothly. Higher engineering cost but professional result. Worth doing for the v1 customer-facing product.

### 8.3 Claude Analyst Layer — Your Direct Transferable Skill

The NXT Bioscience build you described — Claude connected to a knowledge base via MCP for natural language queries — maps directly to this:

```
AFMA analyst: "Show me all vessels that went RF-dark in the Timor Sea 
in the last 72 hours and are consistent with Chinese squid jigger 
operational patterns"

Claude (with MCP access to your TimescaleDB): 
→ Queries dark_vessel_events filtered by bounding box + time window
→ Queries rf_fingerprint_classifications for vessel type probability
→ Runs similarity search against known Chinese squid jigger behaviour profiles
→ Returns ranked list with risk scores + map coordinates + summary paragraph

Analyst reviews, confirms, and tasks Maritime Border Command patrol asset.
```

This is the entire intelligence workflow, delivered as a natural language interface. No training required. One analyst does the work of five.

---

## Part 9: The Key Books and Reference Materials

### 9.1 Essential Textbooks

- **"Introduction to Radio Frequency Design" — Wes Hayward (ARRL):** The RF fundamentals reference. Antenna theory, transmission lines, noise figure calculations. Not maritime-specific but foundational.

- **"Software Defined Radio for Engineers" — Travis Collins et al. (Analog Devices, free PDF):** The SDR Bible. Covers IQ sampling, ADC design, filtering, modulation. Directly applicable. Download free at analog.com.

- **"Statistical Signal Processing" — Louis Scharf:** The mathematical foundations of cross-correlation, hypothesis testing, Cramér-Rao bounds. Heavy going but the actuarial maths transfers.

- **"Bayesian Data Analysis" — Gelman et al. (3rd ed.):** The standard reference for Bayesian modelling. Your dark vessel risk scores will be posterior distributions; this is the theoretical foundation.

- **"Deep Learning" — Goodfellow, Bengio, Courville (free online):** Chapter 10 (RNNs/LSTMs) is the foundation for trajectory prediction models.

### 9.2 Key Papers to Read in Full

1. **Gioia et al. (2020), "Multi-Network Asynchronous TDOA Algorithm Test in a Simulated Maritime Scenario," Sensors, DOI: 10.3390/s20071842** — The most directly relevant academic paper. Maritime TDOA with mixed synchronous/asynchronous nodes. Read this before building anything.

2. **Musicki & Koch, "Geolocation using TDOA and FDOA measurements," IEEE** — Combined TDOA/FDOA theory. The mathematical foundation for vessel geolocation.

3. **arXiv:2502.01503, "Sea-cret Agents: Maritime Abduction for Region Generation to Expose Dark Vessel Trajectories" (Feb 2025)** — The current state of the art in dark vessel trajectory reconstruction. Read this to understand what you're building toward.

4. **arXiv:2002.05013, "Machine Learning-Assisted Anomaly Detection in Maritime Navigation Using AIS Data"** — Taxonomy of anomalies and ML approaches. The reference for your anomaly detection layer design.

5. **arXiv:2508.07668, "AIS-LLM: A Unified Framework for Maritime Trajectory Prediction" (2025)** — The LLM-based approach to AIS intelligence. Validates the Claude analyst layer you're building.

6. **Knapp & Carter (1976), "The Generalized Correlation Method for Estimation of Time Delay," IEEE Transactions on Acoustics, Speech and Signal Processing, Vol. ASSP-24(4)** — The original GCC-PHAT paper. Still the standard 50 years later. Read it.

### 9.3 Online Communities and Forums

- **rtl-sdr.com** — The central hub for RTL-SDR projects. The TDOA and AIS sections are directly relevant.
- **reddit.com/r/RTLSDR** — Active community for SDR troubleshooting
- **GNU Radio Discuss mailing list** — Signal processing implementation questions
- **Radioscanner.ru** — Russian-language but has detailed TDOA implementation discussions
- **sdr.hu / kiwisdr.com** — KiwiSDR network directory; study their TDOA implementation

---

## Part 10: The Sovereign Differentiation Thesis

The competitive analysis resolves to a simple matrix:

| Capability | Hawkeye 360 | Unseenlabs | Windward | **Your platform** |
|---|---|---|---|---|
| Coverage of Aus northern approaches | Periodic | Periodic | Aggregates others | **Persistent / real-time** |
| Sovereign Australian hosting | No (US) | No (France) | No (Israel) | **Yes** |
| ITAR-free | No | Yes | Partial | **Yes** |
| Latency | 15–45 min | Hours | Hours | **<30 seconds** |
| RF fingerprinting | Yes | Yes | Via Unseenlabs | **Yes (built in)** |
| Natural language interface | No | No | Basic | **Yes (Claude MCP)** |
| Civilian customer revenue path | No | Limited | Yes | **Yes (AFMA, ABF)** |
| PROTECTED classification capability | No | No | No | **Yes (AUCloud)** |
| Price point for AFMA/ABF | Too expensive | Not marketed here | Not maritime-ops | **Right-sized for AUS govt SME** |

The sovereign persistent coverage argument is insurmountable for the Australian government customer. No US or French satellite can provide continuous real-time coverage of the Timor Sea. Ground-based nodes can.


## Compliance and lawful collection boundary

Boobook should be architected as a metadata-first system. Early prototypes should focus on AIS reception, controlled test transmissions and non-content RF metadata. Do not record VHF voice content, satellite-phone payloads or private communications. Live deployments require an ACMA/TIA review, a clear lawful basis, and written customer authorisation.

---

*Document version: June 2026. Research based on academic literature to August 2025, competitive intelligence to June 2026.*
