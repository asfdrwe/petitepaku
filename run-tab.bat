@echo off
chcp 65001 >nul

:: バッチ直下の .cache\huggingface を絶対パスで取得
set "HF_CACHE_DIR=%~dp0.cache\huggingface"

:: Windows Terminalを起動
:: 各タブの cmd /k 内で直接 set を実行して環境変数を確実に引き渡します
start "" wt ^
  -d "%~dp0." --title "LLM" cmd /k ".\llamacpp\llama-server.exe -m .\llamacpp\gemma-4-E2B-it-Q4_K_M.gguf" ; ^
  -d "%~dp0Irodori-TTS-Server" --title "TTS" cmd /k "set HF_HOME=%HF_CACHE_DIR%&& set IRODORI_HF_CHECKPOINT=Aratako/Irodori-TTS-v4.1-Small-Quantized/int8-weight-only&& uv run --no-sync python -m irodori_openai_tts --host 0.0.0.0 --port 8088" ; ^
  -d "%~dp0." --title "MAIN" cmd /k "set HF_HOME=%HF_CACHE_DIR%&& uv run --no-sync python main.py"
