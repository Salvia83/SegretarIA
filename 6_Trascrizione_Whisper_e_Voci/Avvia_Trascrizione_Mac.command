#!/bin/bash
# ==============================================================================
# SegretarIA - Avvio Rapido Trascrizione Locale su macOS (1-Click)
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "======================================================================"
echo "🎙️  SEGRETARIA - TRASCRIZIONE AUDIO LOCALE (macOS)"
echo "======================================================================"

VENV_DIR="$HOME/.segretaria_mac_env"

if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Primo avvio rilevato: creazione ambiente virtuale in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "[*] Installazione librerie IA (Faster-Whisper, SpeechBrain, Torch)..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install "av<19" faster-whisper torch torchaudio soundfile speechbrain
fi

echo "[*] Avvio motore di trascrizione e riconoscimento vocale..."
"$VENV_DIR/bin/python3" "$DIR/segretaria_transcribe_diarize.py"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "[✓] Elaborazione completata con successo!"
    osascript -e 'display notification "Trascrizione completata e archiviata!" with title "SegretarIA"' 2>/dev/null
else
    echo ""
    echo "[-] Si è verificato un errore durante l'elaborazione."
fi

echo ""
echo "Premi INVIO per chiudere..."
read -r
