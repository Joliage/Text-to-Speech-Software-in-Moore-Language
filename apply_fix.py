#!/usr/bin/env python3
"""
apply_fix.py  —  Run once from your TTS_Project1 folder:
    python3 apply_fix.py
"""
import os, sys, shutil, ast

TARGET = "tonal_tts_full.py"
if os.path.exists(TARGET):
    shutil.copy(TARGET, TARGET + ".bak")
    print(f"Backup saved: {TARGET}.bak")

CODE = r'''#!/usr/bin/env python3
"""tonal_tts_full.py — Mooré concatenative TTS"""
import os, sys, re, json, threading, subprocess, shutil, io
from dataclasses import dataclass
from typing import Optional, List, Dict

from pydub import AudioSegment
from pydub.playback import play
from pydub.generators import Sine


@dataclass
class SyllableUnit:
    token: str
    path:  str
    audio: Optional[AudioSegment] = None

    def load(self):
        if self.audio is None:
            self.audio = AudioSegment.from_file(self.path)


class SyllableDB:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.units: Dict[str, SyllableUnit] = {}
        # paren_index["ra3"] -> unit for R_AA_3_(Ra3)
        self.paren_index: Dict[str, SyllableUnit] = {}
        # bare_stem_index["aad"] -> unit for AA_AA_D_3_(aad3 (aand3))
        # bare_stem_index["ra"]  -> first Ra unit (fallback)
        self.bare_stem_index: Dict[str, SyllableUnit] = {}
        self._load()

    def _load(self):
        meta = {}
        try:
            meta = json.load(open(os.path.join(self.folder_path, "meta.json"), encoding="utf-8"))
        except Exception:
            pass

        for dirpath, _, files in os.walk(self.folder_path):
            for fname in sorted(files):
                if not fname.lower().endswith(".wav"):
                    continue
                token = os.path.splitext(fname)[0]
                full  = os.path.join(dirpath, fname)
                if token not in self.units:
                    self.units[token] = SyllableUnit(token=token, path=full)

        for t, u in self.units.items():
            m = re.search(r'\(([^)]+)\)', t)
            if not m:
                continue
            paren_content = m.group(1).strip()
            k = paren_content.lower()
            if k not in self.paren_index:
                self.paren_index[k] = u
            first_word = paren_content.split()[0]
            bare = re.sub(r'\d+', '', first_word).lower()
            if bare and bare not in self.bare_stem_index:
                self.bare_stem_index[bare] = u

        for alias, canon in meta.get("aliases", {}).items():
            if canon in self.units:
                self.units[alias] = self.units[canon]

        print(f"[SyllableDB] {len(self.units)} tokens, {len(self.bare_stem_index)} bare stems "
              f"from: {self.folder_path}")

    def get(self, token: str) -> Optional[SyllableUnit]:
        if not token:
            return None
        if token in self.units:
            return self.units[token]
        low = token.lower()
        for k, u in self.units.items():
            if k.lower() == low:
                return u
        nd = re.sub(r'\d+$', '', token)
        if nd and nd != token:
            if nd in self.units:
                return self.units[nd]
            for k, u in self.units.items():
                if k.lower() == nd.lower():
                    return u
        pm = re.search(r'\(([^)]+)\)', token)
        if pm:
            stem = pm.group(1).strip()
            hit  = self.paren_index.get(stem.lower())
            if hit:
                return hit
            if stem in self.units:
                return self.units[stem]
        return self.paren_index.get(low) or self.bare_stem_index.get(low)

    def available_tokens(self) -> List[str]:
        return list(self.units.keys())

    def tokens_in_folder(self, folder: str) -> Dict[str, str]:
        """Return {bare_stem: actual_token} for WAVs directly in `folder`.
        e.g. {'ra': 'R_AA_3_(Ra3)', 'wan': 'W_AA_N_2_(Wan2)', 'san': 'S_AA_N_2_(San2)'}
        This tells us exactly which tone was recorded for each syllable in
        this specific sentence.
        """
        folder_real = os.path.normcase(os.path.realpath(folder))
        result: Dict[str, str] = {}
        for token, unit in self.units.items():
            unit_folder = os.path.normcase(os.path.realpath(os.path.dirname(unit.path)))
            if unit_folder == folder_real:
                m = re.search(r'\(([^)]+)\)', token)
                if m:
                    first_word = m.group(1).strip().split()[0]
                    bare = re.sub(r'\d+', '', first_word).lower()
                    if bare and bare not in result:
                        result[bare] = token
        return result


def build_db(root_db: str, sentence_name: Optional[str] = None):
    if sentence_name:
        for p in [os.path.join(root_db, sentence_name),
                  os.path.join(root_db, sentence_name.replace(" ", "_"))]:
            if os.path.isdir(p):
                return SyllableDB(p)
    return SyllableDB(root_db)


class Mapper:
    def __init__(self, db: SyllableDB, lexicon_path: Optional[str] = None):
        self.db      = db
        self.lexicon: Dict[str, List[str]] = {}
        if lexicon_path and os.path.exists(lexicon_path):
            try:
                self.lexicon = json.load(open(lexicon_path, encoding="utf-8"))
            except Exception:
                pass

        self.diphthongs  = ["ai","au","ei","oi","ou","ia","ie","io","ua","ue","uo","eu"]
        self.triphthongs = ["iau","uai","eau","iou"]

        combined = (list(db.available_tokens())
                    + list(self.lexicon.keys())
                    + list(db.bare_stem_index.keys())
                    + self.diphthongs + self.triphthongs)
        self.keys_short = sorted(set(combined), key=len)  # shortest-first for DP

        # sentence_tokens: {bare_stem: actual_token} for the selected sentence folder.
        # Built by set_sentence_folder(). Empty = no sentence selected yet.
        self.sentence_tokens: Dict[str, str] = {}

    def set_sentence_folder(self, folder: str):
        """Call when user selects a sentence. Builds the preference map for that folder."""
        self.sentence_tokens = self.db.tokens_in_folder(folder)

    def _best(self, token_list: List[str]) -> List[str]:
        """Return the single best matching token from a lexicon entry.

        Priority:
          1. Token whose bare stem is in sentence_tokens (exact tone for this sentence)
             Returns the STORED token name from the DB, not the lexicon string.
          2. Any token that exists anywhere in the DB.
             Returns the stored token name.
          3. First token in list (fallback — synthesizer will try bare_stem_index).
        """
        if not token_list:
            return []

        # Priority 1: pick the token that matches what was actually recorded
        # in the currently selected sentence folder.
        if self.sentence_tokens:
            for t in token_list:
                # Get the bare stem of this lexicon entry e.g. "R_AA_3_(ra3)" -> "ra"
                m = re.search(r'\(([^)]+)\)', t)
                if m:
                    first_word = m.group(1).strip().split()[0]
                    bare = re.sub(r'\d+', '', first_word).lower()
                    if bare in self.sentence_tokens:
                        # Return the STORED token name so db.get() always works
                        return [self.sentence_tokens[bare]]

        # Priority 2: any token that exists anywhere in DB, return stored name
        for t in token_list:
            u = self.db.get(t)
            if u is not None:
                return [u.token]   # ← return u.token, not t (fixes case mismatch)

        return [token_list[0]]

    def _dp(self, word: str) -> List[str]:
        """DP split: fewest unmatched chars, shortest-key bias."""
        n    = len(word)
        best = [None] * (n + 1)
        best[0] = ([], 0)
        for i in range(1, n + 1):
            cand_a = None
            if best[i-1] is not None:
                pk, pu = best[i-1]
                cand_a = (pk + [word[i-1]], pu + 1)
            cand_b = None
            for key in self.keys_short:
                j = i - len(key)
                if j < 0 or best[j] is None:
                    continue
                if word[j:i].lower() != key.lower():
                    continue
                pk, pu = best[j]
                c = (pk + [key], pu)
                if cand_b is None or (c[1], len(c[0])) < (cand_b[1], len(cand_b[0])):
                    cand_b = c
            if (cand_b is not None and
                    (cand_a is None or
                     (cand_b[1], len(cand_b[0])) <= (cand_a[1], len(cand_a[0])))):
                best[i] = cand_b
            else:
                best[i] = cand_a
        return best[n][0] if best[n] else [word]

    def map_word(self, word: str) -> List[str]:
        if not word.strip():
            return []

        w = word.strip().lower()

        # Lexicon first — _best() uses sentence_tokens to pick the right tone
        if w in self.lexicon:
            return self._best(self.lexicon[w])

        # "ra3"-style: orthographic + explicit tone digit
        mt = re.match(r'^(.+?)([123])$', w)
        if mt:
            orth, tone = mt.group(1), mt.group(2)
            if orth in self.lexicon:
                prefer = [t for t in self.lexicon[orth]
                          if re.search(r'\(' + re.escape(orth) + tone + r'\)', t, re.I)]
                return self._best(prefer or self.lexicon[orth])

        # Direct DB hit — return u.token (actual stored name)
        u = self.db.get(word) or self.db.get(w)
        if u is not None:
            return [u.token]

        # DP split for multi-syllable words
        result = []
        for piece in self._dp(w):
            if piece in self.lexicon:
                result.extend(self._best(self.lexicon[piece]))
            else:
                hit = self.db.bare_stem_index.get(piece.lower())
                result.append(hit.token if hit else piece)
        return result

    def map_sentence(self, sentence: str) -> List[str]:
        if '_' in sentence or '(' in sentence:
            out = []
            for chunk in sentence.split():
                if chunk:
                    u = self.db.get(chunk)
                    out.append(u.token if u else chunk)
            return out
        return [t for w in re.findall(r"[A-Za-z0-9\-\u00C0-\u024F]+", sentence)
                    for t in self.map_word(w)]


class Synthesizer:
    def __init__(self, db: SyllableDB, crossfade_ms: int = 10):
        self.db           = db
        self.crossfade_ms = crossfade_ms

    def synthesize(self, tokens: List[str],
                   fallback_db: Optional[SyllableDB] = None) -> Optional[AudioSegment]:
        output = None
        for tok in tokens:
            unit = self.db.get(tok)
            if unit is None and fallback_db:
                unit = fallback_db.get(tok)
            seg = AudioSegment.silent(duration=50)
            if unit is not None:
                unit.load()
                seg = unit.audio or seg
            cf     = min(self.crossfade_ms, len(output), len(seg)) if output else 0
            output = (seg if output is None else
                      output.append(seg, crossfade=cf) if cf > 0 else output + seg)
        return output


def gather_examples(folder: str, mapper: Mapper, max_n: int = 10) -> List[str]:
    for name in ["examples.txt", "transcript.txt", "sentences.txt"]:
        p = os.path.join(folder, name)
        if not os.path.isfile(p):
            continue
        try:
            out = []
            with open(p, encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    s = ln.strip()
                    if s:
                        out.append(s)
                        if len(out) >= max_n:
                            return out
            if out:
                return out
        except Exception:
            pass
    tokens = sorted(mapper.db.available_tokens())
    out, step = [], max(1, len(tokens) // max_n)
    for i in range(0, len(tokens), step):
        if len(out) >= max_n:
            break
        chunk = tokens[i:i+4]
        if chunk:
            out.append(" ".join(chunk))
    return out


_proc: Dict = {'p': None}

# Path to a temp WAV file in the Windows filesystem (accessible to PowerShell)
_WIN_TEMP_WAV = "/mnt/c/Users/Public/tts_playback.wav"

def _stop_audio():
    p = _proc['p']
    if p is not None:
        try: p.terminate(); p.wait(timeout=1)
        except Exception: pass
        _proc['p'] = None

def _win_path(linux_path: str) -> str:
    """Convert a Linux WSL path like /mnt/c/foo to a Windows path like C:\\foo."""
    try:
        r = subprocess.run(['wslpath', '-w', linux_path],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    # Manual fallback: /mnt/c/foo -> C:\foo
    if linux_path.startswith('/mnt/'):
        parts = linux_path[5:].split('/', 1)
        drive = parts[0].upper() + ':\\'
        rest  = parts[1].replace('/', '\\') if len(parts) > 1 else ''
        return drive + rest
    return linux_path

def _find_powershell() -> Optional[str]:
    """Find powershell.exe on the Windows filesystem mounted in WSL."""
    candidates = [
        '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Try PATH (works if WSL interop is enabled)
    r = subprocess.run(['which', 'powershell.exe'], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None

# Will be set to the GUI status2 label so _play_audio can report errors
_status_label = None

def _play_audio(audio_seg: AudioSegment):
    """Play audio. Tries every available backend and reports which one worked."""
    _stop_audio()
    pcm = audio_seg.set_frame_rate(44100).set_channels(1).set_sample_width(2)
    buf = io.BytesIO()
    pcm.export(buf, format='wav')
    wav_bytes = buf.getvalue()

    def _report(msg):
        if _status_label:
            try: _status_label.config(text=msg)
            except Exception: pass

    # ── Option 1: PowerShell (Windows audio — works on Zoom) ────────────────
    ps = _find_powershell()
    if ps:
        try:
            with open(_WIN_TEMP_WAV, 'wb') as f:
                f.write(wav_bytes)
            win_path = _win_path(_WIN_TEMP_WAV)
            ps_cmd = (
                f"$sp = New-Object System.Media.SoundPlayer '{win_path}';"
                f"$sp.Load(); $sp.PlaySync()"
            )
            p = subprocess.Popen(
                [ps, '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            _proc['p'] = p
            def _wait_ps():
                out, err = p.communicate(timeout=30)
                if p.returncode != 0 and err:
                    _report(f"PowerShell error: {err.decode(errors='replace').strip()[:80]}")
            threading.Thread(target=_wait_ps, daemon=True).start()
            return
        except Exception as e:
            _report(f"PowerShell failed: {e} — trying aplay")

    # ── Option 2: aplay (Linux ALSA) ─────────────────────────────────────────
    if shutil.which('aplay'):
        try:
            p = subprocess.Popen(
                ['aplay', '-q'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _proc['p'] = p
            def _feed_aplay():
                try:
                    out, err = p.communicate(input=wav_bytes, timeout=30)
                    if p.returncode != 0 and err:
                        _report(f"aplay error: {err.decode(errors='replace').strip()[:80]}")
                except Exception as e:
                    _report(f"aplay exception: {e}")
            threading.Thread(target=_feed_aplay, daemon=True).start()
            return
        except Exception as e:
            _report(f"aplay failed: {e} — trying pydub")

    # ── Option 3: pydub ───────────────────────────────────────────────────────
    _report("Using pydub fallback")
    threading.Thread(target=lambda: play(audio_seg), daemon=True).start()


def start_gui(synth: Synthesizer, mapper: Mapper):
    import tkinter as tk

    root = tk.Tk()
    root.title("Tonal TTS")
    root.geometry("820x540")
    root.configure(bg="#F0F0F0")

    sel = tk.Frame(root, bg="#F0F0F0")
    sel.pack(fill="x", padx=8, pady=(6, 4))
    tk.Label(sel, text="Sentence folder:", bg="#F0F0F0").pack(side="left", padx=(0, 6))

    try:
        db_root     = mapper.db.folder_path
        has_subdirs = os.path.isdir(db_root) and any(
            os.path.isdir(os.path.join(db_root, e)) for e in os.listdir(db_root))
    except Exception:
        db_root = "."; has_subdirs = False

    sent_root = db_root if has_subdirs else (os.path.dirname(db_root) or db_root)
    try:
        sent_dirs = sorted(d for d in os.listdir(sent_root)
                           if os.path.isdir(os.path.join(sent_root, d)))
    except Exception:
        sent_dirs = []

    sent_var  = tk.StringVar(root, value=sent_dirs[0] if sent_dirs else "")
    menu_vals = sent_dirs if sent_dirs else ["(none)"]

    def on_sentence_change(*_):
        chosen = sent_var.get()
        if chosen and chosen != "(none)":
            folder = os.path.join(sent_root, chosen)
            # Build the sentence-scoped preference map
            mapper.set_sentence_folder(folder)
            create_btns(gather_examples(folder, mapper))
            n = len(synth.db.available_tokens())
            toks = mapper.sentence_tokens
            status.config(
                text=f"{chosen}  |  {len(toks)} syllables in this sentence  |  {n} total")

    sent_var.trace_add("write", on_sentence_change)
    tk.OptionMenu(sel, sent_var, *menu_vals).pack(side="left", padx=(0, 8))

    db_lbl = os.path.basename(mapper.db.folder_path.rstrip("/\\")) or mapper.db.folder_path
    status = tk.Label(sel, text=f"DB: '{db_lbl}'  ({len(mapper.db.units)} tokens)",
                      anchor="w", bg="#F0F0F0", fg="#006600")
    status.pack(side="left", padx=(8, 0))
    tk.Button(sel, text="Reload",
              command=lambda: on_sentence_change()).pack(side="left", padx=(8, 0))

    tk.Label(root, text="Type a word or syllables. Wait 0.5 s or press Enter to hear it.",
             anchor="w", bg="#F0F0F0", fg="#333").pack(fill="x", padx=8, pady=(8, 4))

    ex_outer = tk.Frame(root, bg="#F0F0F0")
    ex_outer.pack(fill="x", padx=8, pady=(0, 6))
    tk.Label(ex_outer, text="Examples:", bg="#F0F0F0").pack(anchor='w')
    wrap = tk.Frame(ex_outer, bg="#F0F0F0")
    wrap.pack(fill='x', pady=2)

    def create_btns(ex_list):
        for c in wrap.winfo_children():
            c.destroy()
        if not ex_list:
            tk.Label(wrap, text="(none)", bg="#F0F0F0", fg="#999").grid(row=0, column=0)
            return
        colors = ["#8A2BE2", "#5F9EA0", "#FF7F50", "#3CB371"]
        for i, key in enumerate(ex_list[:10]):
            def _cmd(k=key):
                txt.delete('1.0', 'end')
                txt.insert('1.0', k)
                do_play()
            lbl = (key[:20] + "…") if len(key) > 20 else key
            tk.Button(wrap, text=lbl, width=22, bg=colors[i % 4], fg="white",
                      command=_cmd).grid(row=i // 4, column=i % 4, padx=3, pady=3)

    txt = tk.Text(root, height=7, width=98)
    txt.pack(padx=8, pady=(2, 6))
    txt.focus_set()
    txt.tag_configure("diph", foreground="red")

    status2 = tk.Label(root, text="Ready — select a sentence folder, then type.",
                       anchor="w", bg="#F0F0F0", fg="#333")
    status2.pack(fill="x", padx=8, pady=(0, 8))
    global _status_label
    _status_label = status2

    def _highlight():
        content = txt.get("1.0", "end-1c").lower()
        txt.tag_remove("diph", "1.0", "end")
        for dt in mapper.diphthongs + mapper.triphthongs:
            s = 0
            while True:
                idx = content.find(dt, s)
                if idx == -1: break
                txt.tag_add("diph", f"1.0+{idx}c", f"1.0+{idx+len(dt)}c")
                s = idx + 1

    def do_play():
        try:
            _do_play()
        except Exception as e:
            try: status2.config(text=f"Error: {e}")
            except Exception: pass

    def _do_play():
        raw = txt.get("1.0", "end").strip()
        if not raw:
            status2.config(text="Type something above.")
            return
        tokens   = raw.split() if re.search(r"\d", raw) else mapper.map_sentence(raw)
        filtered = [t for t in tokens if synth.db.get(t) is not None]
        missing  = [t for t in tokens if synth.db.get(t) is None]

        if missing:
            # Convert ARPABET tokens back to readable bare stems for the message
            def _bare(tok):
                m = re.search(r'\(([^)]+)\)', tok)
                if m:
                    return re.sub(r'\d+', '', m.group(1).strip().split()[0]).lower()
                return tok
            missing_words = list(dict.fromkeys(_bare(t) for t in missing))
            msg = f"Not recorded yet: {missing_words}"
            if filtered:
                msg += f"  |  playing: {filtered[:3]}"
            status2.config(text=msg)
            if not filtered:
                return

        audio = synth.synthesize(filtered, fallback_db=getattr(synth, "fallback_db", None))
        if not audio:
            status2.config(text="Synthesis produced no audio.")
            return
        _play_audio(audio)
        if not missing:
            preview = " + ".join(filtered[:5]) + ("…" if len(filtered) > 5 else "")
            status2.config(text=f"▶  {preview}  ({len(audio)/1000:.2f}s)")
        _highlight()

    deb = {'job': None}
    def on_key(event):
        if deb['job']: root.after_cancel(deb['job'])
        deb['job'] = root.after(450, do_play)
    def on_enter(event):
        if deb['job']: root.after_cancel(deb['job'])
        do_play()
        return "break"
    txt.bind("<KeyRelease>", on_key)
    txt.bind("<Return>",     on_enter)

    if sent_dirs:
        on_sentence_change()
    root.mainloop()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db",            default="Arpabet Transcription")
    p.add_argument("--sentence", "-s", default=None)
    p.add_argument("--fallback-db",   default=None)
    p.add_argument("--lexicon",       default="lexicon_filtered_all.json")
    p.add_argument("--gui",           action="store_true")
    p.add_argument("--play",          default=None)
    args = p.parse_args()
    db     = build_db(args.db, args.sentence)
    lex    = args.lexicon if os.path.exists(args.lexicon) else None
    mapper = Mapper(db, lexicon_path=lex)
    synth  = Synthesizer(db, crossfade_ms=12)
    if args.fallback_db and os.path.isdir(args.fallback_db):
        if os.path.realpath(args.fallback_db) != os.path.realpath(args.db):
            synth.fallback_db = build_db(args.fallback_db)
    if args.play:
        s      = args.play.strip()
        tokens = s.split() if re.search(r"\d", s) else mapper.map_sentence(s)
        tokens = [t for t in tokens if db.get(t)]
        if not tokens: sys.exit("No playable tokens.")
        audio = synth.synthesize(tokens)
        if audio: audio.export("demo_output.wav", format="wav"); play(audio)
        sys.exit(0)
    if args.gui:
        start_gui(synth, mapper)
        sys.exit(0)
    print("CLI. 'exit' to quit.")
    while True:
        s = input(">>> ").strip()
        if s.lower() in ("exit","quit"): break
        if not s: continue
        tokens = mapper.map_sentence(s)
        tokens = [t for t in tokens if db.get(t)]
        if not tokens: print("No playable tokens."); continue
        audio  = synth.synthesize(tokens)
        if audio: threading.Thread(target=lambda: play(audio), daemon=True).start()

if __name__ == "__main__":
    main()
'''

try:
    ast.parse(CODE)
except SyntaxError as e:
    sys.exit(f"Syntax error: {e}")

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(CODE)
print(f"Syntax OK. {TARGET} written.")
print("\nNow run:  ./prepare_and_run_gui.sh")
