# A Text-to-Speech Software in Mooré Language

**Naomie Dalhia Johanne Bambara**
Master's Plan C Defense — May 2026

**Thesis Committee**
- Dr. Mark Petzold — Advisor
- Dr. Koffi N. Ettien — Co-advisor
- Dr. Jie H. Meichsner

Saint Cloud State University · Department of Computer Science

---

## Table of Contents

1. [Introduction](#introduction)
2. [Burkina Faso and the Mooré Language](#burkina-faso-and-the-mooré-language)
3. [Speech Technology Landscape](#speech-technology-landscape)
4. [TTS Theories and Approach Selection](#tts-theories-and-approach-selection)
5. [Why Syllable Concatenation](#why-syllable-concatenation-is-right-for-mooré)
6. [Data Collection](#data-collection-building-the-foundation)
7. [System Architecture](#system-architecture-component-overview)
8. [Core Classes](#core-classes-syllabledb--mapper)
9. [Technical Problems & Solutions](#technical-problems--solutions)
10. [Getting Started](#getting-started)
11. [Evaluation](#evaluation-methodology)
12. [Results](#evaluation-results)
13. [Limitations](#current-limitations)
14. [Future Work](#future-work)
15. [Broader Impact](#broader-implications--impact)
16. [References](#references)

---

## Introduction

This project presents the **first-ever Text-to-Speech (TTS) system for the Mooré language**, spoken by approximately 8 million people worldwide. Mooré currently has no existing digital speech tools, and the adult literacy rate in Burkina Faso stands at just 41.2% (UNESCO).

**Technical Approach:**
- Python + NLP techniques
- Syllable-level concatenative synthesis
- Manual Praat annotation
- Tone preservation across 3 tonal levels (high, mid, low)

**Why This Matters:**
- 📚 **Access to Education** — Non-literate speakers can hear educational content in their own language
- 🏥 **Health Information** — Medical guidance delivered in Mooré reaches those who need it most
- 🌍 **Digital Inclusion** — 8 million people gain a voice in the digital world

---

## Burkina Faso and the Mooré Language

| Statistic | Value |
|-----------|-------|
| Mooré speakers worldwide | ~8 million |
| Mossi ethnic group in Burkina Faso | 52% |
| Adult literacy rate (UNESCO 2022) | 41.2% |
| Female literacy rate | 32.7% |

Mooré is the primary language of Ouagadougou (the capital of Burkina Faso). It has a historically oral tradition with limited written materials and no existing digital resources — no spell checkers, no machine translation, and no TTS. This project delivers the first functional TTS system for the Mooré language.

---

## Speech Technology Landscape

Major voice assistants like Siri (Apple), Alexa (Amazon), and Google Assistant serve billions of users. Unfortunately, many African languages — including Mooré — do not yet have this capability. This project is the first-ever TTS system built for Mooré.

---

## TTS Theories and Approach Selection

| Approach | Status | Rationale |
|----------|--------|-----------|
| **Formant Synthesis** | ❌ Rejected | Mechanical output; unnatural sound; cannot preserve Mooré tonal contours |
| **Di-phone Concatenation** | ❌ Rejected | Thousands of units required; impractical for low-resource languages; no Mooré di-phone database exists |
| **Syllable Concatenation** | ✅ Chosen | Pre-recorded syllables; far fewer units than di-phones; preserves natural tone + timbre; feasible with Praat annotation |

---

## Why Syllable Concatenation is Right for Mooré

- **🎵 Tone is Syllable-Level** — In Mooré, tone (high/mid/low) spans the entire syllable nucleus. Splitting at the phoneme level destroys the tonal contour, changing meaning. ~1,000 syllables needed.
- **🎙️ Natural Voice Preserved** — Concatenating whole recorded syllables keeps the speaker's natural timbre, vowel quality, and intonation intact, with no synthetic artifacts.
- **📐 Diphthongs & Triphthongs** — Complex vowel sequences are kept as single units, guaranteeing correct pronunciation for sounds like */yibeoo/*.
- **⚖️ Feasible at This Scale** — Mooré's syllable inventory is ~1,000 units, which is practical to record manually.

---

## Data Collection: Building the Foundation

### Recording Setup
- Native speaker from Ouagadougou
- Quiet environment with professional microphone
- 100 carrier sentences
- 44.1 kHz, 16-bit WAV format
- Multiple tone variations

### Processing Pipeline
1. Manual Praat syllable cutting
2. ARPABET encoding (tone levels 1–3)
3. JSON lexicon generation
4. WAV normalization
5. Quality verification

> **Example:** `R_AA_3_(Ra3).wav` = syllable **Ra** at **HIGH** tone (3)

### Final Dataset
- **862** syllable tokens
- **442** lexicon entries
- **100** sentence folders
- **3** tone variations per syllable

---

## System Architecture: Component Overview

Python-based modular pipeline:

```
GUI (Tkinter) → Mapper → SyllableDB → Synthesizer → Audio Output
```

| Component | Role |
|-----------|------|
| **GUI** (Tkinter) | Live typing with real-time feedback |
| **Mapper** | Text → ARPABET conversion, dynamic programming syllable splitter |
| **SyllableDB** | 862-token index with 3 lookup strategies |
| **Synthesizer** | Concatenation with crossfading |
| **Audio Output** | PowerShell / aplay WAV playback |

### Key Design Decisions
- **Lazy loading:** Audio segments loaded only when first needed (memory efficient)
- **Multi-tier lookup:** 5-level cascade ensures maximum token coverage
- **Sentence-scoped tone:** `tokens_in_folder()` preserves original context tone
- **Process isolation:** Separate audio subprocess prevents WSL crashes

---

## Core Classes: SyllableDB & Mapper

### SyllableDB — Audio Database

Indexes all 862 WAV tokens from the folder tree using three indexes:
- `units`: exact token → `SyllableUnit`
- `paren_index`: `'(Ra3)'` content → token
- `bare_stem_index`: `'ra'` → `'R_AA_3'`

**5-Level Lookup Cascade:**
1. Exact match (case-sensitive)
2. Case-insensitive match
3. Strip digits: `'Ra'` from `'Ra3'`
4. Parentheses content lookup
5. Bare stem fallback

### Mapper — Linguistic Layer

Converts typed text → ARPABET tokens.

**Key Methods:**
- `set_sentence_folder()` — Loads tone map for selected sentence context
- `_best()` — Selects correct tone variant from `sentence_tokens`
- `_dp()` — Dynamic programming syllable splitter (minimizes unmatched characters)
- `map_word()` — Tries lexicon → DP split → ARPABET direct

**DP Splitter Example:**
```
'yeelam' → 'yee' + 'lam' ✓  (correct)
  NOT     'yeel' + 'am' ❌
```

### Synthesizer — Audio Concatenation

Joins token audio into a final output signal:
1. Iterate over ARPABET token list
2. Retrieve `SyllableUnit` from DB
3. Call `unit.load()` (lazy loading)
4. Append with crossfade (5–20 ms)

**Supporting Scripts:**
- `mfcc_eval.py` — MFCC + DTW objective evaluation (token similarity measurement)
- `manifest_to_lexicon_from_manifests.py` — Builds JSON lexicon (442 entries) from CSV manifests
- `run_on_typing.py` — Keypress launcher for rapid testing without full GUI

---

## Technical Problems & Solutions

### Problem 1: WSL Application Crash
- **Symptoms:** Application crashed on any keystroke with silent failure — no logs, no traceback.
- **Solution:** Used `aplay` subprocess (Linux ALSA) with complete OS-level process isolation to avoid Python-ALSA interaction.

### Problem 2: Incorrect Word Syllable Splits
- **Symptoms:** Greedy algorithm produced wrong splits (e.g., `'yeelam'` → `'yeel' + 'am'` instead of `'yee' + 'lam'`).
- **Solution:** Replaced with a Dynamic Programming (DP) splitter that evaluates all splits simultaneously, minimizes unmatched characters, and prefers shorter valid keys.

### Problem 3: Wrong Tone Selection
- **Symptoms:** System played the wrong tone variant (e.g., `ra1` instead of `ra3`), picking the first match alphabetically and producing incorrect meaning.
- **Solution:** Implemented `tokens_in_folder()` method — scans the selected sentence folder and maps bare stems to actual tokens, preserving original context tone.

### Problem 4: Overlapping Audio Playback
- **Symptoms:** Multiple audio clips played simultaneously during rapid typing.
- **Solution:** Created `_stop_audio()` function that calls `p.terminate()` and `p.wait(timeout=1)` before every new playback, guaranteeing a single audio process.

### Problem 5: Incomplete Database Indexing
- **Symptoms:** SyllableDB only scanned the root folder, finding ~10 tokens instead of 862.
- **Solution:** Replaced `os.listdir()` with `os.walk()` to recursively traverse all 100 sentence sub-folders and index every `.wav` file.

### Problem 6: Silent Playback During Zoom Demos
- **Symptoms:** No audio during screen-sharing because WSL ALSA doesn't reach the Windows audio mixer.
- **Solution:** Added a PowerShell audio backend that exports to a Windows temp directory, converts the path with `_win_path()`, and runs `System.Media.SoundPlayer.PlaySync()` as a subprocess routed through the Windows mixer.

---

## Getting Started

### Prerequisites
- **Python 3.10.12** (project-tested)

### Installation

```bash
# 1. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate          # Ubuntu/macOS
# .\\venv\\Scripts\\Activate.ps1   # Windows PowerShell

# 2. Install Python dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3. Install system packages (Ubuntu)
sudo apt update
sudo apt install -y ffmpeg libsndfile1 build-essential

# 4. Run the orchestration script (performs all pipeline steps and launches the GUI)
./prepare_and_run_gui.sh
```

---

## Evaluation Methodology

### Test Design
- **Participants:** 3 native Mooré speakers
- **Test sentences:** 2

| Sentence | Text | Translation | Words |
|----------|------|-------------|-------|
| 1 | *Ráwã yèelam tí ãadsã yí wusg zàamẽ zàabre* | "Man said that stars came out a lot yesterday evening" | 8 |
| 2 | *Á watà zaabr la yíbeoogò* | "He comes afternoon and morning" | 5 |

### Evaluation Tasks
1. **Comprehension Test** — Listen and repeat sentences
2. **Transcription Test** — Identify each individual word
3. **Naturalness Rating** — Rate on a scale of 1–4 (4 = Very natural, 1 = Not natural)

---

## Evaluation Results

| Metric | Score | Details |
|--------|-------|---------|
| **Comprehension** | **100%** | All 3 participants correctly recognized both sentences |
| **Transcription** | **97.92%** | Sentence 1: 95.84% (23/24 words); Sentence 2: 100% (15/15 words) |
| **Naturalness** | **3.17 / 4** | Ratings: 3.5, 3.0, 3.0 — rated as "Natural" |

### Key Findings
- Excellent intelligibility validates the concatenative approach
- High word recognition shows proper tone preservation
- Naturalness score indicates room for prosody improvement
- System successful for limited-vocabulary demonstration

---

## Current Limitations

1. **Small Dataset:** Only 100 sentences; 2 used for evaluation with 3 participants
2. **Manual Annotation:** Praat syllable segmentation is accurate but time-consuming
3. **Tone Modification:** Simple librosa pitch-shifting introduces artifacts
4. **No Coarticulation:** Isolated tokens can't reproduce natural transitions
5. **Heuristic Mapping:** ARPABET matching; edge cases need manual cleanup
6. **Small Evaluation:** 3 listeners insufficient for statistical testing

---

## Future Work

### Immediate Priorities
- Expand listening tests (n ≥ 10)
- WORLD vocoder for tone modeling
- Duration & prosody modeling
- Concatenation smoothing

### Long-Term Vision
- Expand corpus (10+ hours of recorded speech)
- Semi-automatic annotation (Montreal Forced Aligner)
- Neural TTS (Tacotron2)
- Deployment applications: language learning apps, accessible e-books, voice assistants

---

## Broader Implications & Impact

### Technical Contributions
- First TTS system for the Mooré language
- Validates the concatenative approach for low-resource African languages
- No GPU/cloud infrastructure required — accessible for developing regions
- Open-source codebase for similar projects

### Practical Applications
- Literacy tools and educational audio
- Accessibility for visually impaired and elderly populations
- Low-cost voice interfaces for local services

---

## Conclusion

This project successfully designed and implemented a text-to-speech system for the Mooré language using syllable concatenation instead of phoneme concatenation. Syllables were annotated using ARPABET notation with numbers 1–3 to mark vowel tones. The system integrates open-source libraries including pydub and librosa for audio processing, TensorFlow for modeling, and spaCy for text normalization. Evaluation with 3 native Mooré speakers demonstrated strong intelligibility (100% comprehension, 97.92% transcription accuracy) and natural-sounding output (3.17/4 naturalness). Future work will focus on expanding the corpus, implementing high-fidelity tonal modeling, semi-automatic annotation, and larger perceptual studies.

---

## References

<details>
<summary>Click to expand full reference list</summary>

1. UNESCO Institute for Lifelong Learning (UIL), "GAL Country Profiles as of December 2021: Burkina Faso," Nov. 2022. [Online](https://www.uil.unesco.org/sites/default/files/medias/files/2022/11/gal_country_profiles_burkina.pdf?hub=90)
2. Migration Policy Institute, "Burkina Faso." [Online](https://www.migrationpolicy.org/country-resource/burkina-faso)
3. CIA, "Burkina Faso — The World Factbook." [Online](https://www.cia.gov/the-world-factbook/countries/burkina-faso/)
4. J. Leclerc, "Language planning in the world," TLFQ, Laval University, 2014. [Online](https://www.axl.cefan.ulaval.ca/)
5. B. Zoungrana, "Thesis Towards a Text-to-Speech System for Moore: Procedure and Analysis," 2012.
6. E. Koffi, "A Tutorial on Acoustic Phonetic Feature Extraction for ASR and TTS Applications in African Languages," *Linguistic Portfolios*, vol. 9, no. 1, p. 11, Jan. 2020.
7. D. Crystal, *A Dictionary of Linguistics and Phonetics*, 6th ed. Oxford, UK: Blackwell, 2008.
8. T. Dutoit, *An Introduction to Text-to-Speech Synthesis*. Dordrecht: Kluwer Academic Publishers, 1997.
9. P. Boersma and D. Weenink, "Praat: Doing phonetics by computer," 2025. [Online](https://www.fon.hum.uva.nl/praat/manual/)
10. Librosa. [Online](https://librosa.org/doc/latest/)
11. pydub. [Online](https://pydub.com/)
12. NVIDIA, "Tacotron2." [GitHub](https://github.com/NVIDIA/tacotron2)
13. Explosion AI, "spaCy." [Online](https://spacy.io/)
14. S. Bird, E. Loper, and E. Klein, "Natural Language Toolkit (NLTK)." [Online](https://www.nltk.org/)
15. J. Kong, "HiFi-GAN." [GitHub](https://github.com/jik876/hifi-gan)
16. SciPy Developers, "SciPy Documentation." [Online](https://docs.scipy.org/doc/scipy/)
17. NumPy. [Online](https://numpy.org/)
18. B. Bechtold, "python-soundfile." [Online](https://python-soundfile.readthedocs.io/)
19. FFmpeg Team, "FFmpeg." [Online](https://ffmpeg.org/)
20. Numba. [Online](https://numba.pydata.org/)
21. A. Géron, *Hands-on Machine Learning with Scikit-Learn and TensorFlow*, 3rd ed. O'Reilly, 2022.
22. TensorFlow. [Online](https://www.tensorflow.org/)
23. PyTorch. [Online](https://pytorch.org/docs/stable/)
24. Python Software Foundation, "tkinter — Python interface to Tcl/Tk." [Online](https://docs.python.org/3/library/tkinter.html)
25. E. Koffi and M. Petzold, "A Tutorial on Formant-Based Speech Synthesis for the Documentation of Critically Endangered Languages," *Linguistic Portfolios*, vol. 11, no. 1, Mar. 2022. [Online](https://repository.stcloudstate.edu/stcloud_ling/vol11/iss1/3/)
26. E. Koffi, D. Fabres, S. Pingili, and G. Chava, "Speech Synthesis by Syllable Concatenation: Experimentation with Betine," *Linguistic Portfolios*, 2024.
27. S. J. Russell and P. Norvig, *Artificial Intelligence: A Modern Approach*, 4th ed. Pearson, 2020.
28. C. C. Aggarwal, *Neural Networks and Deep Learning*. Springer Nature, 2023.
29. I. Goodfellow, Y. Bengio, and A. Courville, *Deep Learning*. MIT Press, 2016. [Online](https://www.deeplearningbook.org/)
30. M. Kabore et al., "Voice Interaction in Moore Language: Study on Isolated Word Recognition in Audio Samples," Jan. 2024. doi: 10.4108/eai.18-12-2023.2348169
31. E. E. B. Adam, "Deep Learning Based NLP Techniques in Text to Speech Synthesis for Communication Recognition," vol. 2, no. 4, pp. 209–215, Dec. 2020. doi: 10.36548/jscp.2020.4.002
32. M. Rashad et al., "An Overview of Text-to-Speech Synthesis Techniques," 2010.
33. I. Isewon, J. Oyelade, and O. Oladipupo, *IJAIS*, vol. 7, no. 2, 2014.
34. V. Ademi and L. Ademi, "Natural Language Processing and Text-to-Speech Technology."
35. A. Trilla, "Natural Language Processing Techniques in Text-to-Speech Synthesis and Automatic Speech Recognition," 2009.

</details>

---

## License

*This project was developed as part of a Master's thesis at Saint Cloud State University.*

---

## Acknowledgments

Special thanks to thesis committee members Dr. Mark Petzold, Dr. Koffi N. Ettien, and Dr. Jie H. Meichsner, and to the native Mooré speakers who participated in the evaluation.
