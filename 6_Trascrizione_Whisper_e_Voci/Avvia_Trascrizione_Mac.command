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
    echo "[✓] Trascrizione completata con successo!"

    # Controllo presenza Ollama per estrazione automatica (Episodio 7)
    if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        EXTRACT_SCRIPT=""
        if [ -f "$DIR/segretaria_extract_ollama.py" ]; then
            EXTRACT_SCRIPT="$DIR/segretaria_extract_ollama.py"
        elif [ -f "$DIR/../7_Cervello_Ollama_Estrazione/segretaria_extract_ollama.py" ]; then
            EXTRACT_SCRIPT="$DIR/../7_Cervello_Ollama_Estrazione/segretaria_extract_ollama.py"
        fi
        if [ -n "$EXTRACT_SCRIPT" ]; then
            echo ""
            echo "======================================================================"
            echo "🧠  OLLAMA RILEVATO: AVVIO ESTRAZIONE INTELLIGENTE & MAPPE MENTALI..."
            echo "======================================================================"
            "$VENV_DIR/bin/python3" "$EXTRACT_SCRIPT"
        fi
    fi

    osascript -e 'display notification "Trascrizione ed estrazione completate!" with title "SegretarIA"' 2>/dev/null
else
    echo ""
    echo "[-] Si è verificato un errore durante l'elaborazione."
fi

echo ""
echo "Premi INVIO per chiudere..."
read -r
