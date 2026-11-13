#!/usr/bin/env python3
"""
SegretarIA - Trascrizione Offline, Silero-VAD e Riconoscimento Voci Note (Episodio 6)
Compatibile al 100% con Linux (Proxmox/Server), macOS (Apple Silicon/Intel) e Windows.
"""

import os
import sys
import glob
import time
import shutil
import re
import subprocess
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
from faster_whisper import WhisperModel
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy

# Fix per Windows: evitare WinError 1314 e caricare DLL NVIDIA CUDA
if sys.platform == "win32":
    _orig_symlink = getattr(os, "symlink", None)
    if _orig_symlink:
        def safe_symlink(src, dst, target_is_directory=False):
            try:
                _orig_symlink(src, dst, target_is_directory)
            except OSError:
                if target_is_directory:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        os.symlink = safe_symlink

    # Rilevamento DLL NVIDIA CUDA da site-packages (cublas, cudnn)
    try:
        site_packages = Path(sys.executable).parent.parent / "Lib" / "site-packages"
        for nvidia_bin in site_packages.glob("nvidia/*/bin"):
            if nvidia_bin.exists():
                try:
                    os.add_dll_directory(str(nvidia_bin))
                    os.environ["PATH"] = str(nvidia_bin) + os.pathsep + os.environ["PATH"]
                except Exception:
                    pass
    except Exception:
        pass

# ==============================================================================
# RISOLUZIONE DINAMICA DELLE CARTELLE (Syncthing o Standalone su Mac, Win, Linux)
# ==============================================================================
def resolve_directories():
    base_candidates = [
        # Percorsi Syncthing su Mac e Windows
        os.path.expanduser("~/SyncThing"),
        os.path.expanduser("~/Syncthing"),
        "E:\\Syncthing",
        "E:\\SyncThing",
        "D:\\Syncthing",
        "D:\\SyncThing",
        "C:\\Syncthing",
        "C:\\SyncThing",
        # Percorso server Linux Proxmox
        "/root",
        # Cartella corrente dello script o Home
        os.path.expanduser("~/SegretarIA"),
        os.path.expanduser("~/Desktop/SegretarIA"),
        str(Path(__file__).resolve().parent.parent),
        str(Path(__file__).resolve().parent),
    ]

    input_dir = None
    archive_dir = None

    for base in base_candidates:
        if not os.path.exists(base):
            continue
        # Cerca cartelle con nome ufficiale Syncthing o numerato
        for in_name in ["SegretarIA - Input", "1_Input", "Input"]:
            p = os.path.join(base, in_name)
            if os.path.exists(p) and input_dir is None:
                input_dir = p
        for arc_name in ["SegretarIA - Archivio", "2_Archivio", "Archivio"]:
            p = os.path.join(base, arc_name)
            if os.path.exists(p) and archive_dir is None:
                archive_dir = p

    # Se non trovate, creale nel percorso predefinito dell'utente
    if not input_dir:
        input_dir = os.path.expanduser("~/SyncThing/SegretarIA - Input")
        os.makedirs(input_dir, exist_ok=True)
    if not archive_dir:
        archive_dir = os.path.expanduser("~/SyncThing/SegretarIA - Archivio")
        os.makedirs(archive_dir, exist_ok=True)

    # Cerca la cartella voci_note (preferibilmente dentro l'Input per Syncthing)
    voices_candidates = [
        os.path.join(input_dir, "voci_note"),
        os.path.join(Path(input_dir).parent, "voci_note"),
        os.path.join(str(Path(__file__).resolve().parent), "voci_note"),
        os.path.expanduser("~/SegretarIA/voci_note"),
        "/root/SegretarIA/voci_note"
    ]
    voices_dir = None
    for vd in voices_candidates:
        if os.path.exists(vd):
            voices_dir = vd
            break
    if not voices_dir:
        voices_dir = os.path.join(input_dir, "voci_note")
        os.makedirs(voices_dir, exist_ok=True)

    return input_dir, archive_dir, voices_dir

INPUT_DIR, ARCHIVE_DIR, VOICES_DIR = resolve_directories()
MODEL_SIZE = "large-v3"
COMPUTE_TYPE = "int8"
SIMILARITY_THRESHOLD = 0.35
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.opus', '.m4a', '.flac', '.aac', '.wma')

def fmt_time(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def get_ffmpeg_binary():
    """Rileva l'eseguibile FFmpeg dal sistema, da imageio_ffmpeg o dalla cartella locale."""
    import shutil
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    local_bin = Path(__file__).parent / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if local_bin.exists():
        return str(local_bin)
    return "ffmpeg"

def load_audio_ffmpeg(path_str):
    """Decodifica universale via FFmpeg a 16 kHz mono float (compatibile Opus, MP3, M4A, WAV)."""
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [
        ffmpeg_bin, "-nostdin", "-v", "error",
        "-i", str(path_str),
        "-f", "s16le", "-ar", "16000", "-ac", "1", "-"
    ]
    try:
        raw = subprocess.check_output(cmd)
    except FileNotFoundError:
        raise RuntimeError(
            f"FFmpeg non trovato nel sistema. Installa 'imageio-ffmpeg' (pip install imageio-ffmpeg) "
            f"oppure installa FFmpeg da https://ffmpeg.org e aggiungilo al PATH."
        )
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return torch.from_numpy(samples).unsqueeze(0)

def clean_speaker_name(filename):
    stem = Path(filename).stem
    cleaned = re.sub(r"_(registratore|telegram|whatsapp|telefono|taschino|\d+)$", "", stem, flags=re.I)
    return cleaned.replace("_", " ").strip()

def process(audio_path):
    print("\n" + "=" * 65)
    print(f"🎙️ SEGRETARIA - ELABORAZIONE AUDIO: {Path(audio_path).name}")
    print("=" * 65)
    print(f"📁 Input   : {INPUT_DIR}")
    print(f"📁 Archivio: {ARCHIVE_DIR}")
    print(f"📁 Voci    : {VOICES_DIR}")
    t0 = time.time()

    # 1. Caricamento traccia audio
    print("\n[1/5] Caricamento traccia audio...")
    full_tensor = load_audio_ffmpeg(audio_path)
    total_seconds = full_tensor.shape[1] / 16000.0
    print(f"      Durata rilevata: {fmt_time(total_seconds)}")

    # 2. Caricamento SpeechBrain ECAPA-TDNN per riconoscimento biometrico
    cache_dir = os.path.expanduser("~/.cache/speechbrain_ecapa")
    print(f"\n[2/5] Caricamento modello biometrico vocale (ECAPA-TDNN)...")
    strategy = LocalStrategy.COPY if sys.platform == "win32" else LocalStrategy.SYMLINK
    device = "cuda" if torch.cuda.is_available() else "cpu"
    spk_classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=cache_dir,
        run_opts={"device": device},
        local_strategy=strategy
    )

    # 3. Creazione impronte vocali dalla cartella voci_note/
    print(f"\n[3/5] Scansione rubrica voci note...")
    known_embeddings = defaultdict(list)
    voice_files = [f for f in glob.glob(f"{VOICES_DIR}/*.*") if f.lower().endswith(AUDIO_EXTENSIONS)]
    
    if not voice_files:
        print("      ⚠️ Nessun campione vocale trovato in voci_note/ (usero' etichetta generica)")
    else:
        for vf in voice_files:
            name = clean_speaker_name(vf)
            try:
                sig = load_audio_ffmpeg(vf).to(device)
                emb = spk_classifier.encode_batch(sig).squeeze()
                known_embeddings[name].append(emb)
                print(f"      • Impronta: {name:<15} (da {Path(vf).name})")
            except Exception as e:
                print(f"      [-] Errore su {vf}: {e}")

    master_voiceprints = {name: torch.stack(embs).mean(dim=0) for name, embs in known_embeddings.items()}

    # 4. Trascrizione con Faster-Whisper + Silero VAD (Full Power: CUDA Tensor Cores o tutti i thread CPU)
    compute_type = "float16" if device == "cuda" else "int8"
    total_cpu_threads = os.cpu_count() or 4
    whisper_threads = 4 if device == "cuda" else total_cpu_threads
    torch.set_num_threads(total_cpu_threads)

    print(f"\n[4/5] Trascrizione con Faster-Whisper '{MODEL_SIZE}' ({compute_type} su {device.upper()})...")
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NVIDIA GPU"
        print(f"      🚀 Accelerazione hardware GPU attiva: {gpu_name} (Tensor Cores / FP16)")
    else:
        print(f"      ⚡ CPU Multi-Threading sbloccato: tutti i {whisper_threads} thread attivi!")

    try:
        model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type, cpu_threads=whisper_threads)
    except Exception as e:
        print(f"      [-] Avviso GPU ({e}) -> Fallback automatico su CPU ({total_cpu_threads} thread)...")
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=total_cpu_threads)

    current_beam_size = 5 if device == "cuda" else 1
    print(f"      Filtraggio silenzi attivo (Silero VAD: min 500ms, Beam: {current_beam_size})...")
    audio_data_np = full_tensor.squeeze().numpy()
    segments, info = model.transcribe(
        audio_data_np,
        language="it",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=current_beam_size
    )

    out_lines = []
    durations = defaultdict(float)
    last_speaker = "Io" if "Io" in master_voiceprints else "Interlocutore"

    print("\n--- TRASCRIZIONE IN CORSO ---")
    for s in segments:
        dur = s.end - s.start
        start_samp = int(max(0, s.start) * 16000)
        end_samp = int(min(total_seconds, s.end) * 16000)
        segment_tensor = full_tensor[:, start_samp:end_samp].to(device)

        speaker = last_speaker
        if dur >= 0.6 and segment_tensor.shape[1] >= 9600 and master_voiceprints:
            emb_seg = spk_classifier.encode_batch(segment_tensor).squeeze()
            best_name = None
            best_sim = -1.0
            for name, v_emb in master_voiceprints.items():
                sim = torch.nn.functional.cosine_similarity(emb_seg, v_emb, dim=0).item()
                if sim > best_sim:
                    best_sim = sim
                    best_name = name
            
            if best_sim >= SIMILARITY_THRESHOLD:
                speaker = best_name
                last_speaker = speaker
            else:
                speaker = "Interlocutore"

        durations[speaker] += dur
        line = f"[{fmt_time(s.start)} -> {fmt_time(s.end)}] [{speaker}]: {s.text.strip()}"
        out_lines.append(line)
        print(" ", line)

    # 5. Generazione Report e Archiviazione
    print(f"\n[5/5] Salvataggio e bilancio dei partecipanti...")
    date_str = time.strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{Path(audio_path).stem}"
    target_dir = Path(ARCHIVE_DIR) / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    total_spoken = sum(durations.values())
    hdr = [
        "=" * 70,
        "🎙️ SEGRETARIA - TRASCRIZIONE AUDIO LOCALE & RICONOSCIMENTO VOCALE",
        "=" * 70,
        f"📁 File originale: {Path(audio_path).name}",
        f"⏱️ Durata totale : {fmt_time(info.duration)}",
        f"🗣️ Tempo parlato  : {fmt_time(total_spoken)}",
        "-" * 70,
        "📊 BILANCIO DEI PARTECIPANTI (% TEMPO PARLATO):"
    ]
    for spk, dur in sorted(durations.items(), key=lambda x: -x[1]):
        pct = (dur / total_spoken * 100) if total_spoken > 0 else 0
        bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
        hdr.append(f"  • {spk:<15} : {fmt_time(dur)} ({pct:5.1f}%)  [{bar}]")
    hdr.append("=" * 70 + "\n\n📝 TRASCRIZIONE DETTAGLIATA:\n")

    out_file = target_dir / "trascrizione.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(hdr) + "\n\n" + "\n\n".join(out_lines))

    # Spostamento audio originale in archivio
    try:
        dest_audio = target_dir / Path(audio_path).name
        if Path(audio_path).resolve() != dest_audio.resolve():
            shutil.move(audio_path, dest_audio)
    except Exception as e:
        print(f"      [-] Avviso spostamento audio: {e}")

    elapsed = time.time() - t0
    print(f"\n[✓] Completato con successo in {elapsed:.1f} secondi!")
    print(f"[✓] Trascrizione: {out_file}")
    return str(out_file)

if __name__ == "__main__":
    audio_files = []
    for ext in AUDIO_EXTENSIONS:
        audio_files.extend(glob.glob(f"{INPUT_DIR}/*{ext}"))
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    elif audio_files:
        target = audio_files[0]
    else:
        # Se vuoto, cerca l'ultimo file archiviato
        archived = []
        for ext in AUDIO_EXTENSIONS:
            archived.extend(glob.glob(f"{ARCHIVE_DIR}/*/*{ext}"))
        if archived:
            target = sorted(archived, key=os.path.getmtime)[-1]
            print(f"[*] Coda vuota: rielaboro l'ultimo file in archivio: {target}")
        else:
            print(f"[-] Nessun file audio trovato in {INPUT_DIR}!")
            sys.exit(1)

    result_txt = process(target)
    
    # Se eseguito su Mac o Windows con interfaccia grafica, apri il file al termine
    if sys.platform == "darwin":
        os.system(f"open '{result_txt}'")
    elif sys.platform == "win32":
        os.system(f'notepad.exe "{result_txt}"')
