# Trascrizione Offline, Filtro VAD e Riconoscimento Voci Note (Episodio 6)

Questo modulo trasforma qualsiasi computer (Server Proxmox Linux, Apple Mac o PC Windows) nel motore di ascolto e trascrizione offline di **SegretarIA**.

---

## 📁 Struttura delle Cartelle

Il sistema cerca e riconosce in automatico le due cartelle sincronizzate di Syncthing:
- **`SegretarIA - Input`**: dove vengono depositati i file audio (`.mp3`, `.wav`, `.ogg`, `.opus`, `.m4a`).
  - Sottocartella **`voci_note/`**: dove salvare i campioni vocali (es. `Io_Registratore.mp3`, `Marco.ogg`, `Sara.opus`).
- **`SegretarIA - Archivio`**: dove viene salvato il file `trascrizione.txt` con le statistiche del parlato e archiviato l'audio originale.

---

## 🚀 Come Avviare la Trascrizione

### 🍎 Su macOS (MacBook, Mac Mini, iMac)
1. Fai doppio clic su **`Avvia_Trascrizione_Mac.command`**.
2. Al primo avvio preparerà in automatico l'ambiente isolato e scaricherà i modelli.
3. Al termine dell'elaborazione, aprirà direttamente la trascrizione formattata in TextEdit!

### 🪟 Su Windows (10 / 11)
1. Fai doppio clic su **`Avvia_Trascrizione_Windows.bat`**.
2. **Download automatico**: se Python non è presente sul computer, lo script scarica e installa in autonomia Python 3.11 ufficiale a 64-bit senza richiedere diritti di amministratore!
3. Al termine dell'elaborazione, salverà il risultato con statistiche e parlato in `SegretarIA - Archivio`!

### 🐧 Su Linux / Server Proxmox
```bash
python3 segretaria_transcribe_diarize.py
```
