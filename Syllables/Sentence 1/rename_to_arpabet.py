# -*- coding: utf-8 -*-
"""
ARPABET WAV Renamer  —  Final Corrected Version (Unicode IPA Support)
======================================================================
Reads all .wav files from folders 1–100 inside "Syllabes Recordings",
converts each filename to its ARPABET notation (with tone numbers),
and saves renamed copies into "Arpabet Transcription" on your Desktop.

Handles BOTH formats found in the recording folders:
  • ASCII syllable notation   e.g.  Ba2.wav  Bi1.wav  Sa3an2.wav
  • Unicode IPA filenames     e.g.  ɩ3.wav  ɛ2.wav  ʊ1.wav  i2.wav
    — including tone-diacritic variants:
        ɩ́ (ɩ high) → IH3    ɩ̀ (ɩ low) → IH1    ɩ (ɩ mid) → IH2
        í (i high) → IY3    ì (i low) → IY1    i (i mid) → IY2
        ɛ́ (ɛ high) → EH3   ɛ̀ (ɛ low) → EH1    ɛ (ɛ mid) → EH2
        ʊ́ (ʊ high) → UH3   ʊ̀ (ʊ low) → UH1    ʊ (ʊ mid) → UH2

HOW TO RUN:
    1. Make sure Python 3 is installed  (https://www.python.org/)
    2. Double-click this script,  OR open a terminal and run:
           python3 rename_to_arpabet.py
    3. Renamed copies appear in:
           C:\\Users\\naomi\\Desktop\\Arpabet Transcription\\
"""

import os
import re
import shutil
import unicodedata

# ── CONFIG ────────────────────────────────────────────────────────────────────
SOURCE_ROOT   = r"C:\Users\naomi\Desktop\Syllabes Recordings"
OUTPUT_FOLDER = r"C:\Users\naomi\Desktop\Arpabet Transcription"
FOLDERS       = [str(i) for i in range(1, 101)]   # "1" through "100"
# ─────────────────────────────────────────────────────────────────────────────

# ── Vowel ARPABET symbols (used when attaching tone digits) ───────────────────
VOWELS_ARP = {
    'AA','AE','AH','AO','AW','AY','EH','ER','EY',
    'IH','IY','OW','OY','UH','UW','IC','YC','UC','AX',
    'EN','EM','EL',
}

# ── Tone diacritic → digit mapping ────────────────────────────────────────────
#   acute  ´  U+0301  = high tone  = 3
#   grave  `  U+0300  = low tone   = 1
#   (no diacritic)    = mid tone   = 2  (digit already in filename)
DIACRITIC_TONE = {
    '\u0301': '3',   # combining acute accent  → tone 3
    '\u0300': '1',   # combining grave accent  → tone 1
}

# ── Unicode IPA base character → ARPABET symbol ───────────────────────────────
#
#   CHARACTER  UNICODE  IPA   ARPABET   Description
#   ─────────  ───────  ───   ───────   ──────────────────────────────
#   ɩ          U+0269   ɩ     IH        lax short i  (as in "it")
#   i          U+0069   i     IY        tense long i (as in "eat")
#   ɛ          U+025B   ɛ     EH        open-mid e   (as in "Ed")
#   ʊ          U+028A   ʊ     UH        lax short u  (as in "hood")
#
IPA_BASE_MAP = {
    '\u0269': 'IH',   # ɩ  → IH
    '\u0069': 'IY',   # i  → IY  (standalone IPA file only; compound 'i' → IH per syllable rules)
    '\u025b': 'EH',   # ɛ  → EH
    '\u028a': 'UH',   # ʊ  → UH
}

# Pre-composed characters that may appear due to font/OS rendering
PRECOMPOSED_MAP = {
    '\u00ed': ('IY', '3'),   # í  = i + acute  → IY tone 3
    '\u00ec': ('IY', '1'),   # ì  = i + grave  → IY tone 1
    '\u00fa': ('UH', '3'),   # ú  = ʊ + acute  → UH tone 3  (ú-like rendering of ʊ́)
    '\u00f9': ('UH', '1'),   # ù  = ʊ + grave  → UH tone 1  (ù-like rendering of ʊ̀)
    '\u00e9': ('EY', '3'),   # é  = e + acute  → EY tone 3
    '\u00e8': ('EY', '1'),   # è  = e + grave  → EY tone 1
}


def parse_ipa_filename(stem: str):
    """
    Try to interpret 'stem' as a standalone IPA character filename.
    Returns (ARPABET_symbol, tone_digit_str) or None if not a pure IPA file.

    Handles:
      ɩ3  ɩ2  ɩ1        (plain ɩ + digit)
      ɩ́3  ɩ́2  ɩ́1       (ɩ + combining acute/grave + digit)
      i3  i2  i1        (plain i + digit)
      í3  ì1            (precomposed i+acute/grave + digit)
      ɛ3  ɛ2  ɛ1        (plain ɛ + digit)
      ɛ́3  ɛ̀1            (ɛ + combining diacritics + digit)
      ʊ3  ʊ2  ʊ1        (plain ʊ + digit)
      ʊ́3  ʊ̀1  ú3  ù1   (ʊ + diacritics or precomposed look-alikes)
    """
    # Normalise to NFC first
    s = unicodedata.normalize('NFC', stem.strip())

    # Try precomposed map first (é, è, í, ì, ú, ù)
    if s and s[0] in PRECOMPOSED_MAP:
        arp_sym, default_tone = PRECOMPOSED_MAP[s[0]]
        # remaining chars should be digit(s) only
        rest = s[1:]
        digits = re.sub(r'\D', '', rest)
        tone = digits if digits else default_tone
        return arp_sym, tone

    # NFD decompose to separate base + combining diacritics
    nfd = unicodedata.normalize('NFD', s)

    # Collect base char, optional combining diacritic, optional digit(s)
    # Pattern: one IPA base char, optional combining char(s), optional digits
    i = 0
    base_char = ''
    combining = ''
    digit_str = ''

    if i < len(nfd) and nfd[i] in IPA_BASE_MAP:
        base_char = nfd[i]
        i += 1
        # Consume any combining diacritics
        while i < len(nfd) and unicodedata.category(nfd[i]) == 'Mn':
            combining += nfd[i]
            i += 1
        # Consume digits
        while i < len(nfd) and nfd[i].isdigit():
            digit_str += nfd[i]
            i += 1
        # Nothing else should remain for a pure IPA file
        if i == len(nfd) and base_char:
            arp_sym = IPA_BASE_MAP[base_char]
            # Determine tone: from digit in name, OR from diacritic
            if digit_str:
                tone = digit_str
            elif combining:
                # Use first recognised diacritic
                tone = next((DIACRITIC_TONE[c] for c in combining
                             if c in DIACRITIC_TONE), '2')
            else:
                tone = '2'   # plain = mid tone
            return arp_sym, tone

    return None   # not a pure IPA filename


def to_arpabet(syllable_raw: str) -> str:
    """
    Convert a syllable string (tone digits embedded) to ARPABET notation.

    COMPLETE VOWEL MAPPING (Final Corrected):
    ──────────────────────────────────────────
    Syllable letter   IPA   ARPABET   Notes
    ───────────────   ───   ───────   ──────────────────────────────────────
    i  (in compound)  ɩ     IH        lax short i      ("it")
    ii / ee           i     IY        tense long i     ("eat")
    e                 e     EY        close-mid e      ("ate")
    ɛ  (Unicode)      ɛ     EH        open-mid e       ("Ed")
    u                 ʊ     UH        lax short u      ("hood")
    uu                u     UW        tense long u     ("two")
    o                 o     OW        mid back o       ("oat")
    oo                o     OW        long back o      ("oat")
    a                 a     AA        open central a   ("odd")
    aa                a     AA        long a           ("odd")

    Unicode IPA standalone filenames:
    ───────────────────────────────────
    ɩ / ɩ́ / ɩ̀   → IH + tone digit
    i / í / ì    → IY + tone digit
    ɛ / ɛ́ / ɛ̀   → EH + tone digit
    ʊ / ʊ́ / ʊ̀   → UH + tone digit
    ú / ù        → UH + tone digit  (precomposed look-alikes)
    """
    # ── Step 1: Try pure Unicode IPA filename ────────────────────────────────
    result = parse_ipa_filename(syllable_raw)
    if result:
        arp_sym, tone = result
        return f"{arp_sym}{tone}" if tone else arp_sym

    # ── Step 2: General ASCII syllable parsing ───────────────────────────────
    s = syllable_raw.lower().strip()
    if not s:
        return ''

    # Single consonant + tone  (e.g. n2, m3, b2, f3)
    m = re.match(r'^([a-z])(\d+)$', s)
    if m:
        c, tone = m.group(1), m.group(2)
        single = {
            'n': 'EN', 'm': 'EM', 'l': 'EL',
            'b': 'B',  'f': 'F',  'd': 'D',  'y': 'Y',
            'r': 'R',  'g': 'G',  'k': 'K',  's': 'S',
            'v': 'V',  'z': 'Z',  'w': 'W',  'p': 'P',  't': 'T',
        }
        if c in single:
            return f'{single[c]}{tone}'

    # Bare syllabic consonants (no tone digit)
    if s == 'n': return 'EN'
    if s == 'm': return 'EM'
    if s == 'l': return 'EL'

    parts = []   # list of [arpabet_symbol, accumulated_tone_digits]
    i = 0
    while i < len(s):
        c = s[i]

        # Digit → attach to nearest preceding vowel, else last phoneme
        if c.isdigit():
            for idx in range(len(parts) - 1, -1, -1):
                if parts[idx][0] in VOWELS_ARP:
                    parts[idx][1] += c
                    break
            else:
                if parts:
                    parts[-1][1] += c
            i += 1
            continue

        matched = False

        # 3-character consonant clusters
        for seq, arps in [('ngr', ['NG', 'R']), ('ndr', ['N', 'D', 'R'])]:
            if s[i:i+len(seq)] == seq:
                for a in arps:
                    parts.append([a, ''])
                i += len(seq)
                matched = True
                break
        if matched:
            continue

        # 2-character sequences
        # IMPORTANT: digraph vowels MUST be listed BEFORE their single-char versions
        #
        #   ii / ee  →  IY   (tense long i)
        #   aa       →  AA   (long a)
        #   uu       →  UW   (tense long u)
        #   oo       →  OW   (long o)  — NOT UW
        #
        for seq, arp in [
            ('ng', 'NG'), ('sh', 'SH'), ('zh', 'ZH'), ('ch', 'CH'), ('dh', 'DH'),
            ('kp', 'KP'), ('gb', 'GB'), ('hh', 'HH'),
            ('ii', 'IY'),   # tense long i   →  IY
            ('ee', 'IY'),   # tense long i   →  IY
            ('aa', 'AA'),   # long a         →  AA
            ('uu', 'UW'),   # tense long u   →  UW
            ('oo', 'OW'),   # long back o    →  OW
        ]:
            if s[i:i+2] == seq:
                parts.append([arp, ''])
                i += 2
                matched = True
                break
        if matched:
            continue

        # Single character — FINAL CORRECTED vowel mapping:
        #
        #   a  → AA    open central a
        #   e  → EY    close-mid e       (EH is reserved for Unicode ɛ)
        #   i  → IH    lax short i ɩ     (IY reserved for digraph 'ii'/'ee')
        #   o  → OW    mid back o
        #   u  → UH    lax short u ʊ     (UW reserved for digraph 'uu')
        #
        vowel_map = {
            'a': 'AA',
            'e': 'EY',   # /e/  →  EY
            'i': 'IH',   # ɩ    →  IH
            'o': 'OW',   # /o/  →  OW
            'u': 'UH',   # ʊ    →  UH
        }
        cons_map = {
            'b': 'B',  'd': 'D',  'f': 'F',  'g': 'G',  'h': 'HH',
            'k': 'K',  'l': 'L',  'm': 'M',  'n': 'N',  'p': 'P',
            'r': 'R',  's': 'S',  't': 'T',  'v': 'V',  'w': 'W',
            'y': 'Y',  'z': 'Z',  'q': 'Q',
        }
        if c in vowel_map:
            parts.append([vowel_map[c], ''])
        elif c in cons_map:
            parts.append([cons_map[c], ''])
        else:
            parts.append([c.upper(), ''])   # unknown character — keep uppercased
        i += 1

    return '_'.join(a + t for a, t in parts)


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    total_copied  = 0
    total_skipped = 0
    errors        = []

    for folder_name in FOLDERS:
        folder_path = os.path.join(SOURCE_ROOT, folder_name)

        if not os.path.isdir(folder_path):
            print(f"  [SKIP] Folder not found: {folder_path}")
            continue

        wav_files = [f for f in os.listdir(folder_path)
                     if f.lower().endswith('.wav')]

        if not wav_files:
            print(f"  [INFO] No .wav files in folder: {folder_name}")
            continue

        print(f"\nFolder {folder_name}  ({len(wav_files)} wav file(s))")

        for wav_file in sorted(wav_files):
            stem         = os.path.splitext(wav_file)[0]
            arpabet_name = to_arpabet(stem)

            if not arpabet_name:
                print(f"    [WARN] Could not convert '{wav_file}' — skipping")
                total_skipped += 1
                continue

            src = os.path.join(folder_path, wav_file)
            dst = os.path.join(OUTPUT_FOLDER, f"{arpabet_name}.wav")

            # Avoid silent overwrites — add source folder number as suffix
            if os.path.exists(dst):
                dst = os.path.join(OUTPUT_FOLDER,
                                   f"{arpabet_name}_folder{folder_name}.wav")

            try:
                shutil.copy2(src, dst)
                print(f"    {wav_file:<30}  →  {os.path.basename(dst)}")
                total_copied += 1
            except Exception as e:
                msg = f"    [ERROR] {wav_file}: {e}"
                print(msg)
                errors.append(msg)
                total_skipped += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  Done!   Copied : {total_copied}")
    print(f"          Skipped: {total_skipped}")
    print(f"  Output folder  : {OUTPUT_FOLDER}")
    if errors:
        print("\n  Errors:")
        for e in errors:
            print(e)
    print("=" * 65)

    # ── Built-in self-test ────────────────────────────────────────────────────
    print("\n  Self-test (verify all conversions):")
    tests = [
        # ── Unicode IPA standalone filenames ──
        ('ɩ3',    'IH3'),    # ɩ high tone
        ('ɩ2',    'IH2'),    # ɩ mid tone
        ('ɩ1',    'IH1'),    # ɩ low tone
        ('ɩ\u0301',  'IH3'), # ɩ + combining acute (no digit)
        ('ɩ\u0300',  'IH1'), # ɩ + combining grave (no digit)
        ('i3',    'IY3'),    # i high tone
        ('i2',    'IY2'),    # i mid tone
        ('i1',    'IY1'),    # i low tone
        ('\u00ed', 'IY3'),   # í  precomposed
        ('\u00ec', 'IY1'),   # ì  precomposed
        ('ɛ3',    'EH3'),    # ɛ high tone
        ('ɛ2',    'EH2'),    # ɛ mid tone
        ('ɛ1',    'EH1'),    # ɛ low tone
        ('ʊ3',    'UH3'),    # ʊ high tone
        ('ʊ2',    'UH2'),    # ʊ mid tone
        ('ʊ1',    'UH1'),    # ʊ low tone
        ('\u00fa', 'UH3'),   # ú  (ʊ acute look-alike)
        ('\u00f9', 'UH1'),   # ù  (ʊ grave look-alike)
        # ── ASCII compound syllables ──────────
        ('Ba2',   'B_AA2'),
        ('Bi1',   'B_IH1'),
        ('Ti3',   'T_IH3'),
        ('Men1',  'M_EY1_N'),
        ('Wun2',  'W_UH2_N'),
        ('Gu1',   'G_UH1'),
        ('Lan2',  'L_AA2_N'),
        ('Rib3',  'R_IH3_B'),
        ('Sag1',  'S_AA1_G'),
        ('bee2',  'B_IY2'),    # 'ee' digraph → IY
        ('boo2',  'B_OW2'),    # 'oo' digraph → OW
        ('buu2',  'B_UW2'),    # 'uu' digraph → UW
        ('n2',    'EN2'),
        ('m3',    'EM3'),
    ]
    all_pass = True
    for stem, expected in tests:
        result = to_arpabet(stem)
        ok     = result == expected
        mark   = '✓' if ok else f'✗  expected {expected}'
        print(f"    {stem:<14}  →  {result:<14}  {mark}")
        if not ok:
            all_pass = False

    print(f"\n  {'All tests passed ✓' if all_pass else 'Some tests FAILED — check mapping above'}")
    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
