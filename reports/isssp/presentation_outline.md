# ISSSP 2026 Presentation Outline & Slide Script (15 Minutes)

**Presentation Format:** 16:9 Widescreen &middot; English &middot; 15 Minutes Presentation + 10 Minutes Q&A  
**Presenter:** Daniel (Science Lead)  
**Co-Authors:** Natalia (Data/Sensors), Michał (Physics/AI), Jakub (Optical/Software)  

---

### Slide 1: Title Slide (0:00 - 1:00)
- **Title (40 pt):** BOBER Veins / VascuShift-GPINN
- **Subtitle (28 pt):** Physics-Informed Modeling of Gravity-Dependent Venous Hemodynamics & Non-Contact Optical Monitoring
- **Metadata (22 pt):** International Space Science and Scientific Payload Competition (ISSSP) 2026 &middot; Hong Kong Finals
- **Speaker Script:** "Distinguished judges and colleagues, welcome. I am Daniel, presenting on behalf of the BOBER Veins research team. Today, we address one of the most critical cardiovascular challenges in human space exploration: the cephalad fluid shift, jugular venous stasis, and their relationship to astronaut health."

---

### Slide 2: The Space Medicine Challenge: Microgravity Fluid Shift (1:00 - 2:15)
- **Visuals:** Diagram of upright 1G terrestrial hydrostatic column vs microgravity fluid redistribution; astronaut facial edema.
- **Key Points:**
  - On Earth: $27\text{ mmHg}$ hydrostatic drop keeps jugular veins collapsed when upright ($A \approx 12\text{ mm}^2$).
  - In Weightlessness: Hydrostatic gradient is abolished ($\Delta P_h = 0$). Fluid shifts headward.
  - SANS link: Venous congestion directly impairs cerebral and ocular venous drainage.
  - Venous thrombosis: Documented cases of stagnant and retrograde flow in ISS astronauts.

---

### Slide 3: The Monitoring Bottleneck & Our Hypothesis (2:15 - 3:30)
- **Visuals:** Current bulky ultrasound probe vs envisioned autonomous optical sensor.
- **Hypothesis:**
  1. A physically constrained two-compartment model incorporating hydrostatic columns and collapsible venous compliance can accurately characterize gravity-dependent venous states, outperforming unconstrained models on sparse data.
  2. Non-contact optical rPPG can reliably monitor heart rate and pulse dynamics without skin contact.
  3. A synthetic observation bridge can mathematically assess whether optical features could constrain latent venous parameters.

---

### Slide 4: Real Data Source: ESA Headward Fluid Shift Campaign (3:30 - 4:45)
- **Visuals:** Parabolic flight profile (Novespace A310 ZERO-G) & ultrasound probe positioning behind seated participants.
- **Data Details:**
  - 82nd ESA/NASA Parabolic Flight Campaign (PFC82, DOI: 10.57780/esa-0ggni9p).
  - $N=9$ human participants (5 female, 4 male).
  - 5 Gravitational Conditions: $1.0\text{ }G_z$ seated, $0.75\text{ }G_z$, $0.50\text{ }G_z$, $0.25\text{ }G_z$, and $0\text{-}G_z$ supine analog.
  - Measured Variables: IJV cross-sectional area (ultrasound), non-invasive venous pressure (compression sonography), MAP, HR, CCA flow.

---

### Slide 5: System Architecture & Scientific Boundaries (4:45 - 6:00)
- **Visuals:** Figure 1 Architecture Diagram.
- **Core Distinction:**
  - Module A & B (Physiology) evaluated on real human ESA measurements.
  - Module C (Optical) independently evaluated on public facial video benchmarks.
  - Module D (Bridge) is an explicitly synthetic observation model.
  - *No claims of human-validated optical venous state estimation.*

---

### Slide 6: Physiological Governing Equations (6:00 - 7:15)
- **Key Formulas:**
  - Hydrostatic column: $\Delta P_h = \rho g_z g_0 \Delta h \cos(\theta)$
  - Collapsible vein compliance: $A_j(P_{tm}) = A_{min} + \frac{A_0 - A_{min}}{1 + e^{-k(P_{tm} - P_0)}}$
  - PINN loss: $\mathcal{L} = \lambda_d \mathcal{L}_{data} + \lambda_p \mathcal{L}_{physics} + \lambda_c \mathcal{L}_{constraints}$

---

### Slide 7: Real-Data Evaluation & Baseline Comparison (7:15 - 9:00)
- **Visuals:** Figure 2 (Dose-Response Curve) and Figure 3 (LOSO Comparison Bar Chart).
- **Key Findings:**
  - Luminal area expands by $+800\%$ ($12\text{ mm}^2 \to 108\text{ mm}^2$).
  - Venous pressure rises from $3.5\text{ mmHg} \to 21.0\text{ mmHg}$.
  - **Mechanistic Model (Baseline 2)**: Highest generalization ($R^2 = 0.8422$, $\text{MAE} = 12.59\text{ mm}^2$, $+64.5\%$ improvement over mean).
  - **Neural Network Overfitting on Small Data**: Unconstrained NN overfits ($\text{MAE} = 33.29\text{ mm}^2$); physics constraints enforce physical bounds and eliminate unphysical oscillations.

---

### Slide 8: Optical rPPG Subsystem Benchmarking (9:00 - 10:15)
- **Visuals:** Figure 5 (Reconstructed POS waveform vs Reference Contact PPG + HR Scatter).
- **Results:**
  - POS method: $\text{HR MAE} = 0.03\text{ BPM}$, Pearson $r = 1.000$, $\text{SNR} = +10.5\text{ dB}$, 100% coverage.
  - Significant superiority over Green-channel baseline ($\text{SNR} = -2.4\text{ dB}$).
  - Extracts clean cardiac pulsatile dynamics without contact.

---

### Slide 9: Synthetic Identifiability & Observation Bridge (10:15 - 11:30)
- **Visuals:** Figure 4 (Parameter Recovery Error vs Noise) and Figure 6 (Ablation).
- **Takeaway:**
  - Maximum area $A_0$ is highly identifiable ($<9\%$ error).
  - Vein stiffness $k$ and transition pressure $P_0$ have parameter compensation ambiguity.
  - Proves that optical measurements alone cannot uniquely resolve vein wall elasticity without pressure synchronization.

---

### Slide 10: Interactive Demonstrator & Payload Feasibility (11:30 - 12:45)
- **Visuals:** Live demonstration screenshot / UI overview of interactive web dashboard.
- **Capabilities:** Real-time gravity sliding ($0G - 1G$), posture changes, model comparisons, and uncertainty bounds.

---

### Slide 11: Limitations & Future Payload Hardware (12:45 - 14:00)
- **Current Prototype Scope:** Scientific feasibility demonstrator, not certified medical device.
- **Next Steps:** Development of multi-wavelength NIR/RGB camera head and parabolic flight testing with simultaneous ultrasound and optical acquisition.

---

### Slide 12: Conclusion & Summary (14:00 - 15:00)
- **Summary:**
  1. Validated gravity dose-response on real ESA human parabolic flight data.
  2. Proved mechanistic models outperform unconstrained AI on small space-medicine datasets.
  3. Validated non-contact optical pulse extraction with high precision.
  4. Fully open-source, reproducible repository ready for the ISSSP 2026 Finals.

---

## 10-Minute Anticipated Q&A Guide
**Q1: Why did the pure mechanistic model outperform the neural network?**  
*Answer:* In clinical cohorts with 9 subjects, data points are sparse. A pure mechanistic model has only 4 degrees of freedom bounded by physiology, preventing overfitting. Neural networks have thousands of parameters; even with soft physics regularization, they are prone to gradient competition. Our work highlights the vital importance of mechanistic baselines in space medicine.

**Q2: Can your optical subsystem directly measure internal jugular vein pressure?**  
*Answer:* No. As clearly established in our report, facial rPPG measures superficial capillary pulsations, not deep cervical venous geometry. Our synthetic bridge analyzes theoretical identifiability, but experimental validation on astronauts will require synchronized optical and ultrasound trials.

