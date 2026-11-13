# SegretarIA - Runner Trascrizione Windows
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "SegretarIA - Trascrizione Locale Windows"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   SEGRETARIA - TRASCRIZIONE AUDIO LOCALE (Windows)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Ricerca interprete Python
$pythonExe = $null

if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $ver = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3") {
            $pythonExe = "python"
        }
    } catch {}
}

if (-not $pythonExe -and (Get-Command py -ErrorAction SilentlyContinue)) {
    try {
        $ver = & py -3 --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3") {
            $pythonExe = "py"
        }
    } catch {}
}

if (-not $pythonExe) {
    $searchPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
        "C:\Python3*\python.exe",
        "C:\Program Files\Python3*\python.exe"
    )
    foreach ($p in $searchPaths) {
        $found = Get-Item $p -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $pythonExe = $found.FullName
            break
        }
    }
}

# 1.1 Download e installazione automatica se non presente
if (-not $pythonExe) {
    Write-Host "`n[*] Python non trovato su questo computer." -ForegroundColor Yellow
    Write-Host "[*] Avvio download automatico di Python 3.11 ufficiale (64-bit)..." -ForegroundColor Yellow
    
    $installerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $installerPath = "$env:TEMP\python-3.11.9-amd64.exe"
    $targetDir = "$env:LOCALAPPDATA\Programs\Python\Python311"
    
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Write-Host "[*] Download in corso da python.org..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        
        Write-Host "[*] Installazione automatica in corso (attendere ~30-60 secondi)..." -ForegroundColor Yellow
        $proc = Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 TargetDir=`"$targetDir`"" -Wait -PassThru
        
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
        if (Test-Path "$targetDir\python.exe") {
            $pythonExe = "$targetDir\python.exe"
            Write-Host "[OK] Python 3.11 installato con successo!" -ForegroundColor Green
        } else {
            throw "Installazione completata ma python.exe non trovato in $targetDir"
        }
    } catch {
        Write-Host "`n[-] Errore durante l installazione automatica: $_" -ForegroundColor Red
        Write-Host "Puoi installare Python manualmente da: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "Ricordati di spuntare: [X] Add python.exe to PATH" -ForegroundColor Yellow
        Read-Host "`nPremi Invio per chiudere"
        exit 1
    }
}

Write-Host "`n[*] Interprete Python rilevato: $pythonExe" -ForegroundColor Green

# 2. Creazione / Controllo Ambiente Virtuale
$venvDir = "$env:USERPROFILE\.segretaria_win_env"
$venvPython = "$venvDir\Scripts\python.exe"
$venvPip = "$venvDir\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "`n[*] Creazione ambiente virtuale isolato in: $venvDir..." -ForegroundColor Yellow
    if ($pythonExe -eq "py") {
        & py -3 -m venv $venvDir
    } else {
        & $pythonExe -m venv $venvDir
    }
    
    if (-not (Test-Path $venvPython)) {
        Write-Host "[-] Errore critico: impossibile creare l ambiente virtuale." -ForegroundColor Red
        Read-Host "`nPremi Invio per chiudere"
        exit 1
    }
    
    Write-Host "[*] Installazione librerie IA (Faster-Whisper, SpeechBrain, Torch, imageio-ffmpeg)..." -ForegroundColor Yellow
    Write-Host "    (Operazione iniziale una tantum, puo richiedere alcuni minuti)" -ForegroundColor Gray
    & $venvPip install --upgrade pip
    & $venvPip install faster-whisper torch torchaudio soundfile speechbrain imageio-ffmpeg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Errore durante l installazione dei pacchetti con pip." -ForegroundColor Red
        Read-Host "`nPremi Invio per chiudere"
        exit 1
    }
}

# 2.1 Verifica e attivazione accelerazione NVIDIA CUDA (Tensor Cores)
$gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "NVIDIA|GeForce|Quadro|RTX" } | Select-Object -First 1
if ($gpu) {
    Write-Host "`n[*] Rilevata GPU NVIDIA: $($gpu.Name)!" -ForegroundColor Green
    $cudaCheck = & $venvPython -c "import torch; print(torch.cuda.is_available())" 2>$null
    if ($cudaCheck -ne "True") {
        Write-Host "[*] Aggiornamento pip e pacchetti di sistema..." -ForegroundColor Gray
        & $venvPython -m pip install --upgrade pip --quiet --disable-pip-version-check
        Write-Host "[*] Attivazione CUDA: installazione pacchetti PyTorch cu121 per Tensor Cores..." -ForegroundColor Yellow
        Write-Host "    (Scaricamento librerie NVIDIA CUDA, operazione una tantum)..." -ForegroundColor Gray
        & $venvPip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --disable-pip-version-check
        & $venvPip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --disable-pip-version-check
    }
}

# 3. Esecuzione Pipeline Python
Write-Host "`n[*] Avvio motore di trascrizione e diarizzazione..." -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$scriptPy = Join-Path $ScriptDir "segretaria_transcribe_diarize.py"
& $venvPython $scriptPy

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[-] Si e verificato un errore durante l elaborazione (Codice: $LASTEXITCODE)." -ForegroundColor Red
} else {
    Write-Host "`n======================================================================" -ForegroundColor Green
    Write-Host "[OK] TRASCRIZIONE COMPLETATA CON SUCCESSO!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "I file e il testo si trovano nella cartella 'SegretarIA - Archivio'." -ForegroundColor Green
}

Write-Host "`nPremi Invio per chiudere questa finestra..."
Read-Host
