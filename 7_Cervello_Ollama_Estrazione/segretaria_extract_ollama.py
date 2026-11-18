#!/usr/bin/env python3
"""
SegretarIA - Motore di Estrazione & Comprensione con Ollama
Episodio 7: "Il Cervello: Estrazione, Task, Mappe Mentali e Trigger Geografici"

Questo script analizza le trascrizioni generate da Whisper/WhisperX (file 'trascrizione.txt')
e interroga Ollama in locale con Structured Output (JSON Schema rigoroso).
Estrae:
  1. Context Priming (risoluzione automatica nomi da premessa vocale)
  2. Router di 6 Template Contestuali (Meeting, Medico, Lezione, Brainstorming, Telefonata, Memo)
  3. Mappa Mentale concettuale in sintassi nativa Mermaid.js
  4. Le 4 Liste Atomiche:
     - Promesse di Luca verso altri (Alta Priorità ⚠️)
     - Task generici
     - Lista della spesa / acquisti
     - Trigger geografici ("Quando arrivo a casa" / "In Italia")
  5. Eventi per Google Calendar (con data/ora normalizzata)
  6. Cassaforte Credenziali (PIN, Wi-Fi, Password dettate a voce)
  7. Tono e registro della conversazione (tone_and_mood)
  8. Tag tematici (#lavoro, #domotica, ecc.)
  9. Prompt pronto per Antigravity / Gemini (se contiene idee di automazione)

Genera:
  - analisi.json: archivio dati machine-readable per Streamlit e Home Assistant
  - appunto.md: nota finale formattata con Mermaid renderizzabile e checkbox
"""

import os
import sys
import json
import glob
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE PREDEFINITA & NORMALIZZAZIONE
# ==============================================================================
def normalize_ollama_host(host_str):
    """Normalizza l'host Ollama (gestisce OLLAMA_HOST=0.0.0.0 tipico dei server Proxmox/Linux)."""
    if not host_str:
        return "http://127.0.0.1:11434"
    if "://" not in host_str:
        host_str = "http://" + host_str
    host_str = host_str.replace("://0.0.0.0", "://127.0.0.1")
    parsed = urllib.parse.urlsplit(host_str)
    if not parsed.port:
        host_str = f"{parsed.scheme}://{parsed.hostname}:11434"
    return host_str

DEFAULT_OLLAMA_HOST = normalize_ollama_host(os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
DEFAULT_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "14400"))  # 4 ore default per elaborazioni notturne CPU
DEFAULT_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "16384"))

# Percorsi di default per SegretarIA (Linux Proxmox o macOS/Windows)
SEARCH_ARCHIVE_DIRS = [
    Path("/root/SegretarIA/2_Archivio"),
    Path.home() / "SyncMela/SegretarIA/2_Archivio",
    Path.home() / "SyncThing/SegretarIA - Archivio",
    Path("./2_Archivio"),
    Path.home() / "SyncMela/SegretarIA/Antigravity/2_Archivio",
]

# ==============================================================================
# JSON SCHEMA PER STRUCTURED OUTPUT
# ==============================================================================
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "context_type": {
            "type": "string",
            "enum": [
                "MEETING_LAVORO",
                "VISITA_MEDICA_SALUTE",
                "LEZIONE_CORSO",
                "BRAINSTORMING_PROGETTO",
                "TELEFONATA_VELOCE",
                "MEMO_PERSONALE"
            ]
        },
        "title": {"type": "string"},
        "executive_summary": {"type": "string"},
        "tone_and_mood": {"type": "string"},
        "attendees": {
            "type": "array",
            "items": {"type": "string"}
        },
        "context_sections": {
            "type": "object",
            "additionalProperties": {"type": "string"}
        },
        "mindmap_mermaid": {"type": "string"},
        "promises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "who": {"type": "string"},
                    "to_whom": {"type": "string"},
                    "commitment": {"type": "string"},
                    "deadline": {"type": "string"}
                },
                "required": ["who", "commitment"]
            }
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "assignee": {"type": "string"},
                    "priority": {"type": "string", "enum": ["alta", "media", "bassa"]},
                    "due_date": {"type": "string"}
                },
                "required": ["task", "priority"]
            }
        },
        "shopping_list": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "string"},
                    "category": {"type": "string"}
                },
                "required": ["item"]
            }
        },
        "location_triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "location": {"type": "string"},
                    "category": {"type": "string", "enum": ["micro", "macro"]},
                    "condition": {"type": "string", "enum": ["arrive", "leave"]}
                },
                "required": ["task", "location", "category", "condition"]
            }
        },
        "calendar_events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "datetime_text": {"type": "string"},
                    "location": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["title", "datetime_text"]
            }
        },
        "credentials": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "service_or_device": {"type": "string"},
                    "username": {"type": "string"},
                    "password_or_pin": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["service_or_device", "password_or_pin"]
            }
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "amazon_links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "search_query": {"type": "string"},
                    "reason": {"type": "string"}
                },
                "required": ["search_query"]
            }
        },
        "prompt_per_antigravity": {"type": "string"}
    },
    "required": [
        "context_type",
        "title",
        "executive_summary",
        "tone_and_mood",
        "attendees",
        "context_sections",
        "mindmap_mermaid",
        "promises",
        "tasks",
        "shopping_list",
        "location_triggers",
        "calendar_events",
        "credentials",
        "tags"
    ]
}

# ==============================================================================
# SYSTEM PROMPT PER OLLAMA
# ==============================================================================
SYSTEM_PROMPT = """Sei l'assistente esecutivo e secondo cervello personale di Luca ('SegretarIA').
Il tuo compito è analizzare la trascrizione di una registrazione vocale o di una riunione ed estrarre tutte le informazioni rilevanti compilando ESCLUSIVAMENTE un oggetto JSON valido conforme allo schema richiesto.

LINEE GUIDA CHIAVE:
1. CONTEXT PRIMING & PARTECIPANTI:
   - Se all'inizio della registrazione Luca fa una premessa vocale introduttiva (es. 'Sto andando in macchina con Matteo, poi al ristorante troveremo Ciccio e Giulia'), sfrutta questa premessa per assegnare i nomi reali agli speaker generici ('SPEAKER_01', 'SPEAKER_02'...) e compila la lista 'attendees'.
   - Se un partecipante parla al telefono con terzi di argomenti esterni, ignora le attività altrui e concentrati solo su ciò che impatta Luca (Filtro Attribuzione Target).

2. ROUTER DEI 6 TEMPLATE (campo 'context_type'):
   - Scegli la categoria più appropriata tra:
     * MEETING_LAVORO: compila in context_sections: "decisioni_prese", "problemi_aperti", "prossimi_passi".
     * VISITA_MEDICA_SALUTE: compila: "sintomi_diagnosi", "terapia_e_farmaci", "esami_prescritti", "controlli_futuri".
     * LEZIONE_CORSO: compila: "concetti_chiave", "definizioni_formule", "esempi_citati", "da_approfondire".
     * BRAINSTORMING_PROGETTO: compila: "idea_principale", "vantaggi_e_svantaggi", "scaletta_operativa", "risorse_necessarie".
     * TELEFONATA_VELOCE: compila: "interlocutore", "motivo_chiamata", "azione_richiesta".
     * MEMO_PERSONALE: compila: "riflessione", "punti_focali".

3. MAPPA MENTALE MERMAID ('mindmap_mermaid'):
   - Genera una stringa valida Mermaid.js con sintassi 'mindmap'.
   - Usa un nodo centrale root((Titolo)) e 3-5 rami principali con sotto-nodi sintetici.
   - Esempio di formato:
     mindmap
       root((Progetto Casa))
         Impianto Elettrico
           Fascette
           Cavi 2.5mm
         Scadenze
           Martedì sopralluogo

4. LE 4 LISTE ATOMICHE (Rigorosa Regola di Atomicità: un'azione per ogni elemento!):
   - 'promises' (ALTA PRIORITÀ): Impegni e promesse assunti da Luca in prima persona verso altri (es. "Ti mando il preventivo entro stasera", "Ti chiamo domani"). Indica chiaramente who: "Luca", to_whom, commitment, deadline.
   - 'tasks': Cose da fare generali (operative, di manutenzione o studio). Indica priorità ("alta", "media", "bassa") e assignee.
   - 'shopping_list': Qualsiasi prodotto, alimento o materiale da acquistare (es. alimenti, ferramenta, elettronica).
   - 'location_triggers': Promemoria vincolati al trovarsi in un luogo specifico (es. "Quando arrivo a casa", "Quando vado al Brico", "Quando sono in Italia").
     * category: "micro" per luoghi precisi (casa, ufficio), "macro" per città o nazioni.
     * condition: "arrive" (quando arrivi) o "leave" (quando parti).

5. CASSAFORTE CREDENZIALI & CALENDARIO:
   - 'credentials': PIN, password dettate, codici antifurto o reti Wi-Fi citate (per le reti Wi-Fi: service_or_device: "Wi-Fi", username: nome della rete/SSID, password_or_pin: password della rete).
   - 'calendar_events': Appuntamenti, visite o sopralluoghi con data e ora indicata nel dialogo.

6. TONO, TAG E SVILUPPO:
   - 'tone_and_mood': descrivi il registro emotivo e relazionale (es. 'Professionale e collaborativo', 'Informale / conviviale', 'Frettoloso / urgente').
   - 'tags': 2-5 hashtag (es. ['#lavoro', '#energia', '#spesa']).
   - 'amazon_links': se viene citato esplicitamente l'acquisto di qualcosa su Amazon, compila query di ricerca.
   - 'prompt_per_antigravity': se nel dialogo Luca esprime un'idea di nuova automazione o codice software per SegretarIA, formula un prompt dettagliato pronto all'uso da incollare in Antigravity/Gemini.

Rispondi ESCLUSIVAMENTE con l'oggetto JSON formattato. Niente saluti, niente markdown introduttivo, solo il JSON."""


# ==============================================================================
# FUNZIONI OPERATIVE
# ==============================================================================
def check_ollama_status(host=DEFAULT_OLLAMA_HOST):
    """Verifica che Ollama sia raggiungibile e restituisce l'elenco dei modelli disponibili."""
    url = f"{host}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            return True, models
    except Exception as e:
        return False, []


def query_ollama_structured(prompt_text, model=DEFAULT_MODEL, host=DEFAULT_OLLAMA_HOST, timeout=DEFAULT_TIMEOUT):
    """Invia il testo a Ollama richiedendo Structured Output con JSON Schema."""
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ecco la trascrizione audio da analizzare:\n\n---\n{prompt_text}\n---"}
        ],
        "format": EXTRACTION_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": DEFAULT_NUM_CTX
        }
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")
    
    print(f"[+] Invio a Ollama ({model}) su {host} (timeout={timeout}s)...")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_res = json.loads(resp.read().decode("utf-8"))
            content = raw_res.get("message", {}).get("content", "")
            duration = time.time() - t0
            print(f"[+] Risposta ricevuta in {duration:.1f} secondi.")
            return json.loads(content)
    except urllib.error.URLError as e:
        print(f"[-] Errore di connessione a Ollama: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"[-] Errore nel decodificare il JSON restituito dal modello: {e}")
        raise


def generate_markdown_note(data, original_transcript_path=None):
    """Genera la nota formattata 'appunto.md' con rendering Mermaid, tabelle ed elenchi."""
    title = data.get("title", "Appunto Senza Titolo")
    context_type = data.get("context_type", "MEMO_PERSONALE")
    summary = data.get("executive_summary", "")
    tone = data.get("tone_and_mood", "Neutro")
    attendees = data.get("attendees", [])
    tags = data.get("tags", [])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    md = []
    md.append(f"# 📝 {title}\n")
    md.append(f"- **Data Elaborazione:** `{now_str}`")
    md.append(f"- **Categoria:** `{context_type}`")
    md.append(f"- **Tono & Registro:** *{tone}*")
    if attendees:
        md.append(f"- **Partecipanti Rilevati:** {', '.join(attendees)}")
    if tags:
        md.append(f"- **Tag:** {' '.join(tags)}")
    md.append("\n---\n")
    
    # BOX PROMESSE DI LUCA (SE PRESENTI)
    promises = data.get("promises", [])
    if promises:
        md.append("## ⚠️ Promesse di Luca verso Altri (Alta Priorità)")
        md.append("> *Questi sono impegni presi direttamente da Luca nel dialogo che non vanno assolutamente dimenticati!*\n")
        for p in promises:
            who = p.get("who", "Luca")
            to_whom = p.get("to_whom", "Interlocutore")
            comm = p.get("commitment", "")
            dl = p.get("deadline", "Nessuna data specificata")
            md.append(f"- [ ] **Verso {to_whom}:** {comm} *(Scadenza: {dl})*")
        md.append("\n---\n")
        
    # EXECUTIVE SUMMARY
    md.append("## 💡 Sintesi Esecutiva")
    md.append(f"{summary}\n")
    
    # SEZIONI SPECIFICHE DEL TEMPLATE
    sections = data.get("context_sections", {})
    if sections:
        md.append("### Dettagli del Contesto")
        for sec_name, sec_content in sections.items():
            label = sec_name.replace("_", " ").title()
            md.append(f"#### {label}")
            md.append(f"{sec_content}\n")
            
    # MAPPA MENTALE MERMAID
    mindmap = data.get("mindmap_mermaid", "")
    if mindmap:
        md.append("## 🧠 Mappa Mentale Concettuale")
        md.append("```mermaid")
        md.append(mindmap.strip())
        md.append("```\n")
        
    # LE LISTE ATOMICHE
    tasks = data.get("tasks", [])
    shopping = data.get("shopping_list", [])
    loc_triggers = data.get("location_triggers", [])
    
    if tasks:
        md.append("## ✅ Cose da Fare (Task Generici)")
        for t in tasks:
            task_desc = t.get("task", "")
            prio = t.get("priority", "media").upper()
            assignee = t.get("assignee", "Non specificato")
            due = t.get("due_date", "")
            due_str = f" *(Entro: {due})*" if due else ""
            md.append(f"- [ ] `[{prio}]` **{task_desc}** — Assegnato a: *{assignee}*{due_str}")
        md.append("")
        
    if shopping:
        md.append("## 🛒 Lista della Spesa & Acquisti")
        for s in shopping:
            item = s.get("item", "")
            qty = s.get("quantity", "")
            cat = s.get("category", "")
            qty_str = f" ({qty})" if qty else ""
            cat_str = f" `#{cat}`" if cat else ""
            md.append(f"- [ ] {item}{qty_str}{cat_str}")
        md.append("")
        
    if loc_triggers:
        md.append("## 📍 Promemoria Basati sulla Posizione (Geofence)")
        md.append("> *Pronti per scattare tramite Home Assistant al rientro o all'arrivo in zona!*\n")
        for lt in loc_triggers:
            task_desc = lt.get("task", "")
            loc = lt.get("location", "")
            cond = "all'arrivo a" if lt.get("condition") == "arrive" else "alla partenza da"
            cat = lt.get("category", "micro")
            md.append(f"- [ ] **{task_desc}** → Attivazione: *{cond} {loc}* (`{cat}`)")
        md.append("")
        
    # EVENTI CALENDARIO
    events = data.get("calendar_events", [])
    if events:
        md.append("## 📅 Eventi Rilevati (Google Calendar)")
        for ev in events:
            ev_title = ev.get("title", "")
            dt = ev.get("datetime_text", "")
            loc = ev.get("location", "")
            loc_str = f" presso *{loc}*" if loc else ""
            desc = ev.get("description", "")
            md.append(f"- **{ev_title}**: `{dt}`{loc_str}")
            if desc:
                md.append(f"  *{desc}*")
        md.append("")
        
    # CASSAFORTE CREDENZIALI
    creds = data.get("credentials", [])
    if creds:
        md.append("## 🔐 Cassaforte Credenziali e Codici")
        md.append("> *Dati sensibili estratti dal dialogo. Copia e conserva in sicurezza!*\n")
        for c in creds:
            srv = c.get("service_or_device", "")
            u = c.get("username", "-")
            p = c.get("password_or_pin", "")
            notes = c.get("notes", "")
            md.append(f"- **Dispositivo/Servizio:** `{srv}`")
            if u and u != "-":
                md.append(f"  - **Utente:** `{u}`")
            md.append(f"  - **Password/PIN:** `{p}`")
            if notes:
                md.append(f"  - **Note:** {notes}")
        md.append("")
        
    # LINK AMAZON
    amz = data.get("amazon_links", [])
    if amz:
        md.append("## 📦 Riacquisto su Amazon")
        for item in amz:
            q = item.get("search_query", "")
            url_orders = f"https://www.amazon.fr/gp/your-account/order-history?search={urllib.parse.quote(q)}"
            url_search = f"https://www.amazon.fr/s?k={urllib.parse.quote(q)}"
            md.append(f"- **{q}**: [🔍 Cerca nei Miei Ordini Amazon]({url_orders}) | [🛒 Cerca nel Catalogo]({url_search})")
        md.append("")
        
    # PROMPT PER ANTIGRAVITY / GEMINI
    prompt_ag = data.get("prompt_per_antigravity", "")
    if prompt_ag:
        md.append("## 🤖 Idea di Sviluppo (Prompt Pronto per Antigravity)")
        md.append("```text")
        md.append(prompt_ag)
        md.append("```\n")
        
    return "\n".join(md)


def process_transcription_file(file_path, model=DEFAULT_MODEL, host=DEFAULT_OLLAMA_HOST, timeout=DEFAULT_TIMEOUT):
    """Elabora un singolo file di trascrizione, interroga Ollama e scrive i file di output."""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"[-] File non trovato: {file_path}")
        return False
        
    print(f"\n=======================================================")
    print(f"[+] Elaborazione Trascrizione: {file_path}")
    print(f"=======================================================")
    
    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()
        
    if not transcript_text.strip():
        print("[-] Il file di trascrizione è vuoto. Salto.")
        return False
        
    target_dir = file_path.parent
    json_output_path = target_dir / "analisi.json"
    md_output_path = target_dir / "appunto.md"
    
    # Chiamata Ollama
    result_json = query_ollama_structured(transcript_text, model=model, host=host, timeout=timeout)
    
    # Salvataggio analisi.json
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    print(f"[+] Salvato file JSON: {json_output_path}")
    
    # Generazione e salvataggio appunto.md
    md_content = generate_markdown_note(result_json, original_transcript_path=file_path)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[+] Salvata Nota Markdown: {md_output_path}")
    
    return True


# ==============================================================================
# MAIN CLI
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="SegretarIA - Modulo di Estrazione e Sintesi Ollama (Episodio 7)"
    )
    parser.add_argument("path", nargs="?", help="Percorso di un file 'trascrizione.txt' o di una cartella contenente trascrizioni")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modello Ollama da usare (default: {DEFAULT_MODEL})")
    parser.add_argument("--host", default=DEFAULT_OLLAMA_HOST, help=f"Host Ollama (default: {DEFAULT_OLLAMA_HOST})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Timeout richiesta HTTP in secondi (default: {DEFAULT_TIMEOUT}s)")
    parser.add_argument("--check", action="store_true", help="Verifica solo la connessione a Ollama e i modelli disponibili")
    args = parser.parse_args()
    args.host = normalize_ollama_host(args.host)
    
    print("[*] SegretarIA - Motore di Estrazione Ollama (Episodio 7)")
    
    # Verifica stato Ollama
    ok, models = check_ollama_status(args.host)
    if not ok:
        print(f"[-] ERRORE: Impossibile contattare Ollama su {args.host}.")
        print("    Assicurati che Ollama sia in esecuzione ('ollama serve' o servizio attivo).")
        sys.exit(1)
        
    print(f"[+] Ollama è attivo su {args.host}. Modelli rilevati: {', '.join(models) if models else 'nessuno'}")
    
    if args.check:
        sys.exit(0)
        
    # Se il modello specificato non è disponibile ma ce ne sono altri, usa il primo disponibile
    chosen_model = args.model
    if chosen_model not in models and models:
        print(f"[!] Modello '{chosen_model}' non trovato. Uso il modello disponibile: '{models[0]}'")
        chosen_model = models[0]
        
    # Risoluzione percorso di input
    target_path = None
    if args.path:
        target_path = Path(args.path)
    else:
        # Cerca cartelle con 'trascrizione.txt' nei percorsi d'archivio standard
        for arch_dir in SEARCH_ARCHIVE_DIRS:
            if arch_dir.exists():
                found_files = list(arch_dir.glob("**/trascrizione.txt"))
                if found_files:
                    # Prendi il più recente
                    found_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    target_path = found_files[0]
                    print(f"[+] Trovata trascrizione recente in archivio: {target_path}")
                    break
                    
    if not target_path or not target_path.exists():
        print("[-] Nessun file di trascrizione specificato o trovato nei percorsi di default.")
        print("    Uso: python3 segretaria_extract_ollama.py /percorso/a/trascrizione.txt")
        sys.exit(1)
        
    if target_path.is_dir():
        txt_files = list(target_path.glob("**/trascrizione.txt"))
        if not txt_files:
            print(f"[-] Nessun file 'trascrizione.txt' trovato dentro la directory {target_path}")
            sys.exit(1)
        for tf in txt_files:
            process_transcription_file(tf, model=chosen_model, host=args.host, timeout=args.timeout)
    else:
        process_transcription_file(target_path, model=chosen_model, host=args.host, timeout=args.timeout)
        
    print("\n[+] Elaborazione completata con successo!")


if __name__ == "__main__":
    import urllib.parse
    main()
