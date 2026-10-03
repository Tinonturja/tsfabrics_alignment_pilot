
# Phase 2. Targeted literature novelty audit

## 2.1 Method and evidence standard

**How the verification was done.**

- Four verification searches ran in parallel, one per target paper, plus one targeted "kill search" for anything that would undermine our contribution. All on 2026-09-30.
- Each was required to reach the **primary text**, report the exact route used, and write NOT ESTABLISHED wherever the text could not be read.

**Evidence labels:**

- **[PRIMARY-FULL]:** method and results sections read.
- **[PRIMARY-PARTIAL]:** some sections of the primary text read.
- **[ABSTRACT]:** abstract only.
- **[TITLE]:** title and metadata only.

**Caveat.** All pages passed through a summarising fetch tool, so every number below must be re-checked in the PDF before it goes into a manuscript. For ST-PaveCLIP, the key numbers were stable across four separate fetches.

## 2.2 The four target papers

### (1) Lu, Xu, Huang 2022: lace video

**Bibliography.** Bingyu Lu, Ding Xu, Biqing Huang (Department of Automation, Tsinghua University). *Deep-learning-based anomaly detection for lace defect inspection employing videos in production line.* Advanced Engineering Informatics 51, 101471. DOI 10.1016/j.aei.2021.101471.

**Access: [PRIMARY-PARTIAL].**

- Read: the ScienceDirect abstract page, which showed the full abstract, keywords, the Introduction, the opening of Methodology, and part of "Implementation details".
- Not read: the full text. It is closed access (Unpaywall shows no open-access copy), and the full-text page returned HTTP 429.

| Field | Finding |
|---|---|
| Task | Pixel-level lace defect detection. A model reconstructs each pixel, and a threshold on reconstruction error decides defect or normal |
| Data / domain | Lace, filmed during weaving in production: 3,600 training frames (about 120 s), 1,200 validation, 3,600 for choosing the threshold, all defect-free. **The test set is one 40 s video with artificial defects** |
| Paradigm | Unsupervised, trained only on normal data. It is a trained deep model (GRU plus time-aware spatial attention), not training-free |
| Video | Yes, and central to the method |
| Cross-frame alignment | **Not established.** None is visible in the text we read. There is a "video pre-processing stage", but its content was not read beyond a 3 x 3 mean filter |
| Mechanism | No optical flow, phase correlation or warping is visible. Temporal structure is learned implicitly by the GRU |
| Memory bank / PatchCore | None visible (a reconstruction approach) |
| Normal-only | Yes |
| Condition-disjoint | No evidence of it. The split is temporal within the same material |
| Wrong-pairing / null controls | None visible |
| Temporal averaging | Not established |
| Novelty claim | That it is **the first to detect fabric defects from video**, with a three-stage framework trained on defect-free video |
| Limitations (evident) | A single test video; artificial defects; about 2 minutes of training video; no cross-condition test |
| **Overlap with us** | **Task level: high.** Normal-only anomaly detection on fabric production video. **Mechanism level: low**, as far as we could read |
| Category | **B. Closely overlapping prior art (task level).** Mechanism overlap is **E, unresolved**, until Section 3 is read |

**Consequence.** We **cannot** claim "first video-based fabric anomaly detection" or "first normal-only fabric video anomaly detection". We must cite this paper as the direct prior art for the task.

### (2) ST-PaveCLIP

**Bibliography.** Siyuan He, Yuchun Huang (corresponding), Chen Wang, Feng Yang, Yifan Li (Wuhan University; Hubei Jiaotou Intelligent Testing Co.). *ST-PaveCLIP: A Spatio-Temporal Vision-Language Framework for Road Anomaly Segmentation in Images and Videos.* Remote Sensing 18(17):2922 (2026). DOI 10.3390/rs18172922.

**Access: [PRIMARY-FULL].** The MDPI PDF was read through Section 5, via the mdpi-res.com asset server. The text cut off near the end of Section 5.

**Correction to our earlier documents.** The first author is **He S.**, not "Li et al." as our novelty audit wrote. The earlier numbers (alpha = 0.7; F1 72.71 vs 63.22; false-positive events 1,490 to 1,274) are **now confirmed** from the primary text. They were correct, but they had been unverified until today.

| Field | Finding |
|---|---|
| Task | Pixel-level segmentation of road-surface anomalies (cracks, potholes, patches) in images and in video from a vehicle-mounted camera |
| Data | DeepCrack (75 training images); G45 (50); six road videos at 1280 x 720, 30 fps; four 30 s clips with masks every 4th frame (1 train, 1 validation, 2 test clips) |
| Paradigm | The image model is **supervised with few labels** (frozen CLIP, trained adapters, Dice and Focal losses on anomaly masks). The **video extension is training-free** |
| Alignment | RoMa v2 dense matching, then a RANSAC homography (5 px threshold). **The previous frame's fused probability map is warped** into the current frame. Outside the valid region, the current prediction is used alone |
| Mechanism | Deterministic registration (pretrained matcher plus RANSAC). Optical flow is used only for the evaluation metrics |
| Fusion rule | **Recursive exponential moving average:** P(t) = alpha x warped history + (1 - alpha) x current. alpha = 0.7 was chosen for temporal consistency, although F1 was best at 0.5. A reset every 2 s, plus a reset when history and current prediction disagree (IoU difference > 0.5) |
| Memory bank / PatchCore | No / no |
| Normal-only | No (trained on anomaly masks) |
| Condition-disjoint | No. The authors state the clips share similar acquisition and road conditions, and caution against reading the results as domain-invariant generalisation |
| Controls | Frame-wise (no fusion); **unwarped EMA (fusion without alignment)**; a weaker matcher (ORB plus homography); sweeps over alpha and the reset interval. **No reversed-shift, lag-permuted or random-homography control** |
| Key results (read) | Pixel F1: frame-wise 71.69; unwarped EMA **63.22**; ORB 72.50; RoMa 72.71. Flicker metric TCE fell about 3x with alignment. False-positive events: frame-wise 1,490; unwarped 1,304; RoMa 1,274. **The 95th-percentile false-positive duration doubled, from 0.133 s to 0.267 s, under aligned recursive fusion.** Cost: 45.6 ms per frame |
| Novelty claim | A CLIP-based road-anomaly framework, auxiliary supervision, a training-free video alignment module, and evaluation with few labels |
| Limitations (stated) | Very small label subsets; no study across datasets or unseen conditions; not evidence of domain-invariant generalisation |
| **Overlap with us** | **Substantial at the operator level:** a frozen per-frame anomaly model, training-free geometric warping of past anomaly maps, fusion, an unaligned-fusion control that performs **worse** than no fusion, and event-level false-positive statistics |
| Category | **B. Closely overlapping prior art** |

**What survives after ST-PaveCLIP:**

- normal-only memory-bank maps instead of supervised ones;
- moving material in front of a fixed camera instead of a moving camera, with a 1-D physics-constrained shift;
- a finite window matched to the physical dwell time, instead of a recursive EMA;
- controls that break *only* the pairing (lag permutation) or direction (reverse);
- condition-group-disjoint evaluation;
- per-pass and per-track units with a persistence cap.

**Its Table 11 is directly useful to us.** It shows that aligned fusion **lengthens** some false alarms. Our ceil(L/25) event rule exists precisely so that longer alarms are charged, so our metric is positioned to detect that failure mode.

### (3) MAP-VD (CVPR Workshops 2026)

**Bibliography (confirmed from the CVF workshop index page).** Sosmita Paul, Krishna Roy. *MAP-VD: Cross Match-Guided Video Diffusion for AM Anomaly Detection.* CVPR 2026 Workshops (Agentic AI for Visual Media, A4VM), pp. 4549-4558.

**Access: [TITLE] only.**

- The CVF PDF and HTML returned HTTP 403 (bot blocking, not a paywall).
- The arXiv, OpenAlex and Semantic Scholar queries were rate-limited.
- No preprint was found.

| Field | Finding |
|---|---|
| Every technical field | **NOT ESTABLISHED** |
| From the title only | Video anomaly detection in additive manufacturing using a video **diffusion** model guided by "cross matching". A diffusion model is almost certainly trained, so it is unlikely to be training-free or memory-bank based. What "cross match" operates on (frames, views, or a reference) is unknown |
| Category | **E. Unresolved.** Do not cite it as overlapping or as non-overlapping until it is read |

**Action.** Open the CVF PDF in a normal browser. Check, in order:

1. what the cross matching operates on;
2. whether there is explicit frame alignment;
3. whether scores are aggregated over time;
4. the training regime;
5. whether any shuffled or wrong-pairing controls are used.

### (4) Isl-Knit

**Bibliography.** Avishek Das Gupta, Zafar Sadek, MD. Shakhawat Hossain, Tarik Reza Toha, Anupom Mondol, Sultana Umme Habiba, Shaikh Md. Mominul Alam. *An approach to automatic fault detection in four-point system for knitted fabric with our benchmark dataset Isl-Knit.* Heliyon 10(17), e35931 (2024). DOI 10.1016/j.heliyon.2024.e35931.

**Access: [PRIMARY-FULL]** (ScienceDirect full-text page; Table 14 is an image and was not verified).

| Field | Finding |
|---|---|
| Task | **Supervised** multi-class object detection (YOLOv5 and YOLOv8) of 7 knit fault types, feeding automated four-point grading |
| Data | 3,375 **still** smartphone photos from 5 knit-dyeing factories in Bangladesh, taken at post-knitting inspection and finishing machines; 8 knit types; bounding boxes, no masks |
| Video / alignment / memory bank / normal-only | No / no / no / no |
| Split | Random 60/10/30 split at the image level. **Not condition-disjoint** |
| Key results (read) | Best mAP@0.5 = 0.694 (YOLOv5m, 640 px); factory trial F1 0.775 |
| Overlap with us | **Domain only** (knitted fabric defects) |
| Category | **C. Related but materially different.** It cannot serve our temporal question, because it has no sequences |

## 2.3 What the kill search added

| Work (access) | Why it matters |
|---|---|
| **Sandia patent US6266437B1**, filed 1998, granted 2001 (primary patent text) | **Registers each camera frame of a moving patterned web** (cross-correlation plus a warp to a reference exemplar) and **accumulates defect evidence sequentially across successive frames**. It is the oldest direct precedent for "register, then accumulate evidence on a moving web". It uses no learned features, no memory bank and no anomaly maps. **Category A/B:** it is why the principle of our operator cannot be claimed as new, even in web inspection |
| **Song and Lee 2026**, arXiv 2608.21854 (FULL) | Uses deliberately broken detectors (a constant score per video, video-mean replacement) as **negative controls in evaluating video anomaly detection**. So "null controls as an evaluation device" has precedent. Our *correspondence-breaking* controls (reverse, lag permutation) were not found anywhere |
| Road obstacle video segmentation, GCPR 2025, arXiv 2509.13181 (FULL) | Supervised. Temporal consistency comes from learned attention, with no explicit warping of maps |
| Glazner et al., arXiv 2511.13944 (ABSTRACT) | Leakage from near-duplicate video frames, fixed by cluster-disjoint splits. Supports our fold design as established practice |
| Smartex patent US20220005182A1 (FULL) | Camera on a circular knitting machine, but the camera rotates with the machine so the fabric appears static. No multi-frame accumulation |
| GeoMAD, arXiv 2608.26724 (TITLE) | Geometry-aware multi-view anomaly detection. Unread; **E** |
| **TSFabrics citations** | **Zero** in both Semantic Scholar and OpenAlex as of 2026-09-30. No anomaly-detection result on TSFabrics exists yet. **This is time-sensitive** |

## 2.4 Novelty matrix

**Key:** Y = yes; N = no; ? = not established; ~ = partial.

| Method | Video | Moving material | Alignment | Memory bank | Training-free | Normal-only | Wrong-pairing control | Condition-disjoint | Main distinction from ours |
|---|---|---|---|---|---|---|---|---|---|
| **Ours (v1.2 pilot)** | Y | Y (fabric past a fixed camera) | Y (phase correlation, deterministic, 1-D) | Y (PatchCore-derived) | Y | Y | **Y (reverse + lag permutation + unaligned)** | **Y (condition groups)** | |
| ST-PaveCLIP 2026 | Y | ~ (moving camera over a road) | Y (RoMa v2 + homography, deterministic) | N | Video stage Y; base model N | N | N (unwarped control only) | N (stated) | Supervised base; recursive EMA; no pairing controls; no held-out conditions |
| Lu et al. 2022 | Y | ? (lace during weaving) | ? (none visible; learned GRU) | N (visible) | N | Y | N (visible) | N | A learned reconstruction model; one artificial-defect test video |
| MAP-VD 2026 | Y (title) | ? | ? | ? | Probably N (diffusion) | ? | ? | ? | Not established |
| Isl-Knit 2024 | N | N | N | N | N | N | N | N (random split) | A supervised still-image detection benchmark |
| VideoPatchCore 2024 | Y | N (surveillance) | N | Y | Y | Y | N | N | No alignment; Gaussian score smoothing (our V1) |
| FGFA 2017 | Y | N | Y (learned flow) | N | N | N | N (unaligned ablation only) | N | Supervised feature aggregation; its unaligned aggregation is worse than single-frame |
| Sandia patent 2001 | Y (frames) | Y (moving web) | Y (registration to an exemplar) | N | Y (rule-based) | ~ (reference exemplar) | N | n/a | No learned features or maps; exemplar registration; sequential test |
| CableInspect-AD 2024 | Y (frames) | ~ (camera moves along the cable) | N | Y (PatchCore) | ~ | Y | N | ~ (split by defect ID) | Frames scored independently |
| AeBAD-V / MMR 2023 | Y | Y (rotating blades) | N | N (PatchCore only as a baseline) | N | Y | N | ~ (held-out views) | Frame-independent scoring |
| SPRT sewer 2025 | Y | ~ (moving robot) | N | N | N | ~ | N | ? | Accumulation **without** alignment |
| TSFabrics / TSFDNet 2026 | Y | Y | N | N | N | N | N | ~ (scenario-disjoint only) | Supervised 3D-CNN + LSTM clips |
| Ni et al. 2025 | Y | Y | N (rules) | N | N | ~ | N | ~ | Rule-based cutline filtering |
| Fabric4show 2024 | Y | Y | ~ (object-ID matching) | N | N | N | N | N | Supervised detection plus de-duplication |
| MVEAD 2025 | N (multi-view stills) | N | Y (epipolar) | Y | N | ? | N | N | Trained cross-view feature fusion |
| Cuellar et al. 2024 | Y | ~ (moving platform) | Y (inertial / homography) | N (RX statistic) | Y | ~ | N | N | Register-then-detect on infrared imagery |
| Song and Lee 2026 | (evaluation) | n/a | n/a | n/a | n/a | n/a | ~ (broken-detector controls) | n/a | Null controls for **metrics**, not for correspondence |

## 2.5 Classification of each element of our design

| Element of our design | Class | Primary evidence |
|---|---|---|
| Align, then aggregate evidence across frames | **A. Established** | FGFA 2017; Farsiu 2004; Sandia patent (moving web); TDI hardware |
| Training-free warping of *anomaly maps* across frames, with an unaligned control | **B. Closely overlapping** | ST-PaveCLIP 2026 (supervised base, homography, recursive EMA) |
| Normal-only anomaly detection on fabric *video* | **B. Closely overlapping** | Lu et al. 2022 (claims to be first) |
| PatchCore or memory banks on video, no alignment | **A. Established** | VideoPatchCore; CableInspect-AD |
| Temporal score smoothing; accumulation lowering false alarms | **A. Established** | VideoPatchCore (Gaussian); SPRT (George et al. 2025) |
| Event- and track-level metrics; group-disjoint splits | **A. Established** | Street Scene; Roberts 2017; Glazner 2025 |
| Normal-only memory-bank maps aligned by a deterministic 1-D global shift on a moving textured material, with a dwell-matched window | **D. Potentially differentiated** | Not found in any paper read, including the kill search |
| **Correspondence-breaking controls (reverse, lag permutation) that hold everything else fixed** | **D. Potentially differentiated** | Not found. ST-PaveCLIP and FGFA use only unaligned controls; Song and Lee use broken detectors, not broken correspondence |
| Condition-group-disjoint, per-pass/per-track, persistence-capped evaluation of inspection video, with a pre-registered decision rule | **D. Differentiated as an integrated protocol** | Each ingredient has precedent; the combination for this data type was not found |
| First anomaly-detection results on TSFabrics | **D (time-sensitive)** | Zero citations today |
| Whether Lu et al. align frames in pre-processing; what MAP-VD's cross matching does; GeoMAD | **E. Unresolved** | Primary texts not read |
