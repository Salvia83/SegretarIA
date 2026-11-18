#!/usr/bin/env python3
"""
SegretarIA - Orchestratore Notturno Unificato (Episodio 7)
Esegue in sequenza dentro LXC 100 (segretaria-worker):
  1. Attende che Syncthing riceva eventuali file in ingresso in 1_Input.
  2. Trascrive e diarizza tutti gli audio in coda in 1_Input tramite WhisperX (segretaria_env).
  3. Analizza con Ollama (qwen2.5:7b) ogni trascrizione in 2_Archivio priva di analisi.json / appunto.md.
  4. Attende il completamento al 100% della sincronizzazione Syncthing verso i nodi attivi
     + un margine di sicurezza (default: 300 secondi / 5 minuti) prima dello spegnimento dell'host.
"""

import os
import sys
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("/root/SegretarIA/1_Input")
ARCHIVE_DIR = Path("/root/SegretarIA/2_Archivio")
WHISPER_PYTHON = Path("/root/segretaria_env/bin/python3")
WHISPER_SCRIPT = Path("/root/SegretarIA/scripts/segretaria_transcribe_diarize.py")
OLLAMA_SCRIPT = Path("/root/SegretarIA/scripts/segretaria_extract_ollama.py")
SYNCTHING_CONFIG = Path("/root/.config/syncthing/config.xml")
SYNCTHING_URL = "http://127.0.0.1:8384"
LOG_FILE = Path("/var/log/segretaria_notte.log")

AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".opus", ".m4a", ".flac", ".aac", ".wma")


def log(msg):
    """Stampa a video e salva nel file di log con timestamp locale."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_syncthing_config(config_path=SYNCTHING_CONFIG):
    """Legge API key e ID cartelle da config.xml di Syncthing."""
    if not config_path.exists():
        return None, {}
    tree = ET.parse(config_path)
    root = tree.getroot()
    apikey = root.findtext("./gui/apikey")
    folders = {}
    for elem in root.findall("./folder"):
        fid = elem.attrib.get("id", "").strip()
        label = elem.attrib.get("label", fid).strip()
        if fid:
            folders[fid] = label or fid
    return apikey, folders


def syncthing_get(endpoint, apikey, timeout=5):
    """Esegue una richiesta GET autenticata alle REST API locali di Syncthing."""
    req = urllib.request.Request(
        f"{SYNCTHING_URL}{endpoint}",
        headers={"X-API-Key": apikey},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def has_syncthing_temp_files(*dirs):
    """Controlla se ci sono file temporanei di trasferimento Syncthing in corso."""
    for base in dirs:
        if not base.exists():
            continue
        for p in base.rglob("*.tmp"):
            if ".syncthing" in p.name or "~syncthing~" in p.name:
                return True
    return False


def wait_for_syncthing(phase_label, max_wait_sec=900, grace_sec=300):
    """Attende che Syncthing completi il trasferimento verso i peer connessi e poi aspetta il margine."""
    apikey, folders = load_syncthing_config()
    if not apikey or not folders:
        log(f"[!] ({phase_label}) Configurazione Syncthing non trovata: attendo {grace_sec}s fissi.")
        if grace_sec > 0:
            time.sleep(grace_sec)
        return

    log(f"[*] ({phase_label}) Verifica sincronizzazione Syncthing ({len(folders)} cartelle)...")
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > max_wait_sec:
            log(f"[!] ({phase_label}) Timeout attesa Syncthing dopo {max_wait_sec}s, procedo comunque.")
            break

        try:
            if has_syncthing_temp_files(INPUT_DIR, ARCHIVE_DIR):
                log(f"[*] ({phase_label}) Trasferimento temporaneo Syncthing in corso, attendo 10s...")
                time.sleep(10)
                continue

            status_data = syncthing_get("/rest/system/status", apikey)
            my_id = status_data.get("myID", "")
            conns_data = syncthing_get("/rest/system/connections", apikey).get("connections", {})
            connected_peers = [
                dev_id for dev_id, info in conns_data.items()
                if dev_id != my_id and info.get("connected")
            ]

            all_synced = True
            pending_notes = []

            for fid, label in folders.items():
                db_stat = syncthing_get(f"/rest/db/status?folder={urllib.parse.quote(fid)}", apikey)
                state = db_stat.get("state", "unknown")
                need_bytes = db_stat.get("needBytes", 0)
                if state != "idle" or need_bytes > 0:
                    all_synced = False
                    pending_notes.append(f"{label}: state={state}, need={need_bytes}B")
                    continue

                for peer in connected_peers:
                    comp = syncthing_get(
                        f"/rest/db/completion?folder={urllib.parse.quote(fid)}&device={urllib.parse.quote(peer)}",
                        apikey,
                    )
                    pct = comp.get("completion", 100)
                    p_need = comp.get("needBytes", 0)
                    if pct < 100 or p_need > 0:
                        all_synced = False
                        pending_notes.append(f"{label}->{peer[:7]}: {pct}% ({p_need}B)")

            if all_synced:
                log(
                    f"[+] ({phase_label}) Syncthing allineato (peer online: {len(connected_peers)}). "
                    f"Attesa di sicurezza: {grace_sec}s..."
                )
                break

            log(f"[*] ({phase_label}) Sync ancora in corso ({'; '.join(pending_notes)}). Attendo 10s...")
        except Exception as exc:
            log(f"[!] ({phase_label}) Syncthing API non ancora pronta ({exc}), riprovo tra 10s...")

        time.sleep(10)

    if grace_sec > 0:
        time.sleep(grace_sec)
        log(f"[+] ({phase_label}) Attesa di sicurezza ({grace_sec}s) completata.")


def find_pending_inputs(input_dir=INPUT_DIR):
    """Trova tutti i file audio reali in attesa in 1_Input (esclusi voci_note e file nascosti/temp)."""
    if not input_dir.exists():
        return []
    files = []
    for p in sorted(input_dir.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith(".") or ".syncthing" in p.name or p.name.endswith(".tmp"):
            continue
        if p.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(p)
    return files


def find_pending_extractions(archive_dir=ARCHIVE_DIR):
    """Trova ogni trascrizione.txt in 2_Archivio che non ha ancora analisi.json o appunto.md."""
    if not archive_dir.exists():
        return []
    pending = []
    for txt in sorted(archive_dir.glob("*/trascrizione.txt")):
        folder = txt.parent
        if not (folder / "analisi.json").exists() or not (folder / "appunto.md").exists():
            pending.append(txt)
    return pending


def run_step(cmd, label):
    """Esegue uno step della pipeline trasmettendo l'output in tempo reale."""
    log(f"[>] Avvio {label}: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        log(f"[-] ERRORE in {label} (exit code {proc.returncode}) dopo {elapsed:.1f}s")
        return False
    log(f"[+] Completato {label} in {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(description="SegretarIA - Pipeline Notturna Unificata LXC 100")
    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa verrebbe elaborato senza eseguire")
    parser.add_argument("--pre-wait", type=int, default=300, help="Secondi di attesa iniziale sync in ingresso (default: 300s = 5 min)")
    parser.add_argument("--step-pause", type=int, default=15, help="Secondi di pausa tra uno step/file e il successivo (default: 15s)")
    parser.add_argument("--grace-seconds", type=int, default=300, help="Secondi extra di attesa prima dello spegnimento (default: 300s = 5 min)")
    parser.add_argument("--skip-sync-wait", action="store_true", help="Salta l'attesa Syncthing")
    args = parser.parse_args()

    log("=================================================================")
    log("🌙 SEGRETARIA - AVVIO PIPELINE NOTTURNA AUTOMATICA (LXC 100)")
    log("=================================================================")

    if not args.skip_sync_wait and not args.dry_run:
        wait_for_syncthing("INGRESSO", max_wait_sec=600, grace_sec=args.pre_wait)

    # 1. Coda Audio -> WhisperX + Diarizzazione (Episodio 6)
    pending_audio = find_pending_inputs()
    log(f"[*] Audio nuovi trovati in 1_Input: {len(pending_audio)}")
    for audio in pending_audio:
        if args.dry_run:
            log(f"    [DRY-RUN] Trascriverei: {audio}")
            continue
        if not WHISPER_PYTHON.exists() or not WHISPER_SCRIPT.exists():
            log(f"[-] Ambiente Whisper mancante ({WHISPER_PYTHON} / {WHISPER_SCRIPT})")
            break
        run_step([str(WHISPER_PYTHON), str(WHISPER_SCRIPT), str(audio)], f"Whisper ({audio.name})")
        if args.step_pause > 0:
            log(f"[*] Pausa tecnica {args.step_pause}s per chiusura processi e flush su disco...")
            time.sleep(args.step_pause)

    # 2. Coda Trascrizioni -> Ollama Structured Output (Episodio 7)
    pending_txt = find_pending_extractions()
    log(f"[*] Trascrizioni in 2_Archivio senza analisi Ollama: {len(pending_txt)}")
    for txt in pending_txt:
        if args.dry_run:
            log(f"    [DRY-RUN] Analizzerei con Ollama: {txt}")
            continue
        if not OLLAMA_SCRIPT.exists():
            log(f"[-] Script Ollama mancante: {OLLAMA_SCRIPT}")
            break
        run_step([sys.executable, str(OLLAMA_SCRIPT), str(txt)], f"Ollama ({txt.parent.name})")
        if args.step_pause > 0:
            log(f"[*] Pausa tecnica {args.step_pause}s per raffreddamento e rilascio memoria...")
            time.sleep(args.step_pause)

    # 3. Attesa completamento Syncthing + margine sicurezza pre-spegnimento
    if not args.skip_sync_wait and not args.dry_run:
        wait_for_syncthing("USCITA PRE-SPEGNIMENTO", max_wait_sec=900, grace_sec=args.grace_seconds)

    log("🏁 PIPELINE NOTTURNA COMPLETATA CON SUCCESSO.")


if __name__ == "__main__":
    main()
