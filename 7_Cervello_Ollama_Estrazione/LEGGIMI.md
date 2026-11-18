# SegretarIA - Episodio 7: Il Cervello (Ollama, Structured Output & Mappe Mentali)

Questa cartella contiene il modulo di intelligenza artificiale per l'analisi e la comprensione dei testi di SegretarIA.

## Contenuto
1. `segretaria_extract_ollama.py`: Script Python che legge `trascrizione.txt`, interroga Ollama in locale con JSON Schema rigido e genera `analisi.json` e `appunto.md`.
2. `esempio_trascrizione_test.txt`: File di trascrizione realistico per collaudare subito il sistema senza registrazioni pregresse.

## Requisiti
- **Ollama installato**:
  - Linux/Proxmox: `curl -fsSL https://ollama.com/install.sh | sh`
  - macOS: `brew install ollama` o scarica da [ollama.com](https://ollama.com)
  - Windows: scarica l'eseguibile da [ollama.com](https://ollama.com)
- **Modello consigliato**:
  ```bash
  ollama pull qwen2.5:7b
  ```
  *(oppure `ollama pull llama3.1:8b`)*

## Come Eseguire
```bash
python3 segretaria_extract_ollama.py esempio_trascrizione_test.txt
```
Lo script produrrà nella stessa cartella:
- `analisi.json`: Dati strutturati machine-readable (per Home Assistant e Streamlit).
- `appunto.md`: Verbale leggibile formattato con mappa mentale grafica Mermaid.js e checkbox.
