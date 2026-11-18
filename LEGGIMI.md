# 📦 SegretarIA - Kit Script Ufficiali (Syncthing, Bot Telegram & Scarico USB)

Questo pacchetto contiene tutti gli script mostrati nella serie YouTube **SegretarIA — Il Secondo Cervello IA 100% in Locale**, già ripuliti e pronti per essere personalizzati con i tuoi dati.

---

## 📂 Contenuto delle Cartelle

### `1_Syncthing_Proxmox_LXC/`
- **`COMANDI_TERMINALE_EP04.txt`**: I 6 comandi esatti mostrati nell'Episodio 4 pronti per il copia-incolla nella Console del Container LXC.
- **`installa_syncthing_lxc.sh`**: Script unico automatico da eseguire nella Console di un Container LXC (Debian/Ubuntu) su Proxmox VE. Installa Syncthing, crea la struttura a 2 cartelle (`/root/SegretarIA/1_Input` e `/root/SegretarIA/2_Archivio`), attiva l'avvio automatico al boot e sblocca l'interfaccia Web sulla rete locale (`0.0.0.0:8384`).

### `2_Bot_Telegram/`
- **`telegram_bot_ingestor.py`**: Il Bot Telegram privato ("Imbuto Universale") scritto in Python 3 standard (**zero librerie esterne da installare**). Riceve note vocali, audio, foto, documenti, testi e link web salvandoli subito in `1_Input`.
  - Apri il file e sostituisci `INSERISCI_QUI_IL_TUO_TOKEN` con il Token fornito da `@BotFather`.
  - Al primo avvio lascia `ALLOWED_USER_ID = 0` e invia `/start` al bot: ti risponderà con il tuo User ID numerico personale da incollare in `ALLOWED_USER_ID` per blindare il bot!
- **`installa_servizio_bot.sh`**: Rende il Bot Telegram un servizio automatico (`systemd`) attivo H24.

### `3_Scarico_USB_Proxmox/` *(Opzione A: Mini-PC Server con Proxmox VE)*
- **`usb_recorder_ingest.sh`**: Scarica i file audio dal registratore vocale USB direttamente nel container LXC (`pct push`), ripara al volo eventuali errori `exFAT` dei chip Jieli, sincronizza data e ora in `MRECSET.txt`, smonta la memoria lasciando attiva la ricarica a `+5V`, riproduce il doppio tono dallo speaker interno e invia una notifica su Telegram.
  - Prima di installarlo, apri `usb_recorder_ingest.sh` e verifica il valore `LXC_ID` (ed eventualmente Token/ID Telegram).
- **`installa_usb_proxmox.sh`**: Eseguilo sulla Shell del nodo principale Proxmox per installare tutto e attivare la regola `udev`.

### `4_Scarico_USB_macOS/` *(Opzione B: Mac)*
- **`mac_usb_recorder_ingest.sh`**: Modifica `TARGET_DIR` con il percorso della tua cartella Syncthing sul Mac.
- **`installa_usb_macos.sh`**: Compila automaticamente la micro-app nativa `SegretarIA_USB.app` (necessaria per il permesso di macOS sui volumi rimovibili) e attiva il guardiano automatico su `/Volumes`.
  - ⚠️ **Nota importante:** Non spostare la cartella dopo aver eseguito `installa_usb_macos.sh` (oppure rieseguilo dalla nuova posizione).

### `5_Scarico_USB_Windows/` *(Opzione C: PC Windows)*
- **`windows_usb_recorder_ingest.ps1`**: Apri il file con Blocco Note e imposta `$TargetDir` sul percorso della tua cartella Syncthing (es. `"D:\Syncthing\SegretarIA - Input"`).
- **`Avvia_USB_Windows.bat`**: Doppio clic per testare subito lo scarico con finestra visibile a schermo.
- **`Installa_Avvio_Automatico_Nascosto.bat`**: Doppio clic (una sola volta) per registrare l'avvio automatico **100% invisibile** a ogni accensione di Windows.

### `6_Trascrizione_Whisper_e_Voci/` *(Episodio 6: Trascrizione Offline, VAD e Riconoscimento Voci)*
- **`segretaria_transcribe_diarize.py`**: Il motore unificato che usa Faster-Whisper (`large-v3`), filtro silenzi Silero VAD, e SpeechBrain ECAPA-TDNN per riconoscere chi parla confrontando con i campioni audio nella cartella `voci_note/` (es. vocali WhatsApp/Telegram). Funziona su Proxmox Linux, macOS e Windows (con supporto automatico GPU NVIDIA CUDA e CPU multithread).
- **`Avvia_Trascrizione_Mac.command`**: Launcher 1-Click per macOS (crea l'ambiente virtuale isolato, trascrive e apre il risultato in TextEdit).
- **`Avvia_Trascrizione_Windows.bat`** + **`windows_transcribe_runner.ps1`**: Launcher 1-Click per Windows 10/11 (scarica Python 3.11 in automatico se assente, attiva CUDA/Tensor Cores su GPU NVIDIA e trascrive tutto).

### `7_Cervello_Ollama_Estrazione/` *(Episodio 7: Ollama Locale, Structured Output & Automazione Notturna)*
- **`segretaria_extract_ollama.py`**: Interroga Ollama in locale (`qwen2.5:7b` / `qwen2.5:32b`) con JSON Schema rigido per generare `analisi.json` e `appunto.md` (Context Priming, 6 Template, Mermaid.js, Promesse, Task, Spesa, Trigger Geografici).
- **`segretaria_pipeline_notturna.py`** + **`segretaria_notte_proxmox_host.sh`** + **`segretaria-notte.service`**: Pipeline notturna unificata per Proxmox (attesa Syncthing, Whisper, Ollama, auto-spegnimento).
- **`esempio_trascrizione_test.txt`**: Trascrizione demo pronta per i primi test offline.

---

## ⚠️ Avvertenza Importante per Registratori USB Economici (Chip Jieli)
**NON impostare mai la cartella `RECORD` come "Nascosta" (`attrib +h`) sulla chiavetta USB!**  
Molti microchip dei registratori vocali tascabili non leggono l'attributo `Hidden` e finiscono per creare una **seconda cartella `RECORD` duplicata** con lo stesso nome, bloccando Esplora File su Windows. Lascia `RECORD` sempre visibile: gli script la svuotano automaticamente in 3 secondi a ogni inserimento!
