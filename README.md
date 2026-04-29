# TTS Project — README

A beginner-friendly guide for the hand-cut syllable TTS system.

This README is a complete, ready-to-paste `README.md` that documents the repository, installation, and how to run the new per-sentence GUI and CLI features (including `--sentence` and fallback DB behavior).

---

# Table of Contents

- What this project is  
- Repo layout (important files)  
- Naming conventions for syllable WAVs  
- Quickstart (minimal)  
  1. Create & activate a virtualenv  
  2. Install dependencies  
  3. Make a quick Sentence-1 test DB  
  4. Generate (or inspect) a lexicon  
  5. Play / Render audio  
- GUI (updated: per-sentence support)  
- `prepare_and_run_gui.sh` (helper script)  
- New CLI flags and behavior  
- How the GUI picks examples (quick buttons)  
- Evaluation (MFCC distances)  
- Troubleshooting & tips  
- Project scripts (what they do)  
- Contributing / License  

---

# Purpose

The purpose of this project is to implement a Text-To-Speech program in the Moore language. Moore is a language spoken primarily in Burkina Faso by the Mossi ethnic group. Moore is predominantly an oral language. The language is spoken by approximately 5 million people in Burkina Faso and about 3 million in Côte d'Ivoire, as well as by around 850,000 speakers in Benin, Ghana, Mali, and Togo. Despite being a widely spoken language, I realized that there is no existing program to convert text to speech in it. I decided to address this issue by implementing text-to-speech software in Python. By using NLP (Natural Language Processing) techniques in Python, the project develops solutions to address the lack of TTS systems for the Moore Language. The development of the system requires a comprehensive linguistic assessment and the acquisition of both audio and textual data. These data are then aligned at the syllable level to form the foundation for machine-learning-based speech synthesis. This technology aims to make information more accessible to non-literate individuals, thereby contributing to efforts to reduce low literacy rates in Burkina Faso. According to the UNESCO Institute for Lifelong Learning [1], the adult literacy rate (ages 15+) in Burkina Faso stands at 41.2% overall, with a significant gender gap: 50.1% for males and 32.7% for females. 

# What This Project Is

A simple text-to-speech (TTS) system built from hand-cut syllable WAV files.

The approach is **concatenative**: short syllable WAV tokens are selected and joined to synthesize words and sentences. The system is intended for tonal languages (example: Mooré) and supports tone digits in token names as well as per-sentence databases for performance.

## Key Design Goals

- Keep the code mostly original (not copy/paste from other open-source projects).
- Support tone digits (1 low, 2 mid/neutral, 3 high) and long vowels.
- Allow fast per-sentence operation by loading only one sentence folder at a time.
- Provide a GUI for quick testing and clickable example phrases.

---

# Repo Layout (Important Files)

```
projects/TTS_Project/
  tonal_tts_full.py
  run_on_typing.py
  prepare_and_run_gui.sh
  mfcc_eval.py
  manifest_to_lexicon_from_manifests.py
  lexicon_from_filenames.json
  lexicon_from_manifests.json
  lexicon_filtered_all.json
  pairs.json
  Arpabet Transcription/
  mfcc_distances.csv
  README.md
  requirements.txt
  venv/
```

## File Descriptions

- `tonal_tts_full.py` — Main synthesizer / demo script (CLI + GUI)  
- `run_on_typing.py` — Tiny helper: press Enter to run `prepare_and_run_gui.sh`  
- `prepare_and_run_gui.sh` — Helper to prepare DB & launch GUI  
- `mfcc_eval.py` — MFCC distance / evaluation utilities  
- `manifest_to_lexicon_from_manifests.py` — Auto-generate lexicon from manifests  
- `lexicon_from_filenames.json` — Auto-generated lexicon stub  
- `lexicon_from_manifests.json` — Auto-generated lexicon stub  
- `lexicon_filtered_all.json` — Filtered lexicon used by GUI  
- `pairs.json` — Combined-token/parts pairs used by MFCC eval  
- `syllables/` — Hand-cut syllable WAVs (organized by Sentence X folders)   
- `mfcc_distances.csv` — MFCC evaluation outputs  
- `requirements.txt` — Python dependencies  
- `venv/` — Optional local virtualenv  

---

# Naming Conventions for Syllable WAVs

Follow these conventions when naming syllable WAV files:

## Tone Digits

Token names include a tone digit at the end:

- `1` = low tone (falling/low)  
- `2` = mid / neutral  
- `3` = high tone (rising/high)  

Example:

```
Ra1.wav
Ra2.wav
Ra3.wav
```

## Long Vowels

Double the vowel letters:

```
Raa1.wav
```

## Compound Rising/Falling

If represented as two-tone sequence:

```
Ra3a1.wav
```

(Orthography convention determines tokenization.)

## Important

The system expects the tone digit to be part of the filename token stem.  
It uses filename stems as token names internally.

---

# Quickstart (Minimal)

Run from project root (where `tonal_tts_full.py` is located).

---

## 1. Create & Activate a Virtualenv

### Linux / macOS / WSL

```
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)

```
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## 2. Install Dependencies

Preferred:

```
pip install --upgrade pip
pip install -r requirements.txt
```

Minimal install:

```
pip install pydub soundfile numpy librosa scipy python-docx
```

Install ffmpeg (required by pydub):

Debian/Ubuntu:

```
sudo apt install ffmpeg
```

---

## 3. Make a Quick Sentence-1 Test DB

```
rm -rf ./syllables_s1
mkdir -p ./syllables_s1
cp "./syllables/Sentence 1/"*.wav ./syllables_s1/ 2>/dev/null || true
ls ./syllables_s1
```

---

## 4. Generate (or Inspect) a Lexicon

Auto-generate starter lexicon:

```
python manifest_to_lexicon_from_manifests.py --root ./syllables --out lexicon_from_manifests.json
```

If no lexicon is present, GUI falls back to filename-derived lexicon.

Lexicon format:

```json
{
  "word": ["TOKEN1", "TOKEN2"]
}
```

---

## 5. Play / Render Audio

### Play a Single Token

```
python tonal_tts_full.py --db ./syllables_s1 --play "Ra3"
```

### Play Tokenized Sequence or Orthographic String

```
python tonal_tts_full.py --db ./syllables --lexicon lexicon_from_manifests.json --play "ra"
```

Per-sentence DB:

```
python tonal_tts_full.py --db ./syllables --sentence "Sentence 1" --play "Ra3 a1 Vi3"
```

### Launch GUI

```
./prepare_and_run_gui.sh
```

Pre-load a sentence:

```
./prepare_and_run_gui.sh "Sentence 1"
```

---

# GUI (Updated: Per-Sentence Support)

New features:

- Sentence folder selector
- Reload button (loads only selected folder)
- Fallback DB (`syllables_all_links`)
- Example quick buttons (up to 10 phrases)
- Highlighted diphthongs/triphthongs
- Optional beep on highlighted tokens

Workflow:

1. Launch GUI  
2. Select "Sentence 1"  
3. Press Reload  
4. Click example or type text  
5. Press Enter to play  

---

# prepare_and_run_gui.sh (Helper Script)

Automates:

- Builds sanitized symlink DB (`syllables_all_links`)
- Generates lexicon JSONs
- Filters lexicon to valid tokens
- Launches GUI
- Optionally pre-loads sentence

Usage:

```
./prepare_and_run_gui.sh
./prepare_and_run_gui.sh "Sentence 1"
SENTENCE="Sentence 1" ./prepare_and_run_gui.sh
```

Make executable:

```
chmod +x prepare_and_run_gui.sh
```

---

# New CLI Flags and Behavior

## `--db PATH`
Root folder containing sentence folders.

## `--sentence "Sentence 1"` (or `-s`)
Loads only that sentence folder.

## `--fallback-db PATH`
Optional global fallback DB.

## `--lexicon PATH`
Path to JSON lexicon.

## `--gui`
Start Tkinter GUI.

## `--play "TEXT"`
One-shot synthesis.

## `--demo`
Console interactive demo.

---

# How the GUI Picks Examples

Priority order:

1. `examples.txt` inside sentence folder  
2. `manifest.csv` transcripts  
3. Filename-derived tokens  
4. If none → "(no examples found)"  

To add examples:

Create:

```
./syllables/Sentence 1/examples.txt
```

One phrase per line (max 10 recommended).

---

# Evaluation (MFCC Distances)

Use `mfcc_eval.py` to compare combined tokens vs split parts.

Example:

```
python mfcc_eval.py --db-root ./syllables_all_links --pairs pairs.json --out mfcc_distances.csv
```

Verbose + auto-combine:

```
python mfcc_eval.py --db-root ./syllables_all_links --pairs pairs.json --out mfcc_distances.csv --auto-combine --verbose
```

Example `pairs.json`:

```json
{
  "combined": "Vi3uu2gu1",
  "split": ["Vi3", "uu2", "gu1"]
}
```

Lower MFCC distance = closer spectral match.

---

# Troubleshooting & Tips

Missing packages:

```
pip install -r requirements.txt
```

ModuleNotFoundError:
- Activate venv.

Playback errors:
- Install ffmpeg.

GUI won’t start:

```
sudo apt install python3-tk
```

Slow startup:
- Use `--sentence "Sentence N"`

Token not found:
- Ensure tone digit at end (e.g., `Ra3.wav`)

Case sensitivity:
- Prefer consistent token casing.

Unknown tokens:
- Run `prepare_and_run_gui.sh`

---

# Project Scripts (What They Do)

- `tonal_tts_full.py` — Main program (CLI + GUI)  
- `prepare_and_run_gui.sh` — Builds DB + launches GUI  
- `run_on_typing.py` — Keypress trigger  
- `manifest_to_lexicon_from_manifests.py` — Build lexicon JSON  
- `mfcc_eval.py` — MFCC + DTW evaluation  
- `map_to_arpabet.py` — ARPABET WAV helpers  
- `pairs.json` — Combined vs split token mappings  

---
