@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: ==========================================
:: 設定エリア（保存先フォルダを指定してください）
:: ==========================================
set "SAVE_DIR=%~dp0llamacpp"

:: ==========================================
:: メイン処理
:: ==========================================
echo ==================================================
echo AIモデルの事前ダウンロードを開始します...
echo 保存先: %SAVE_DIR%
echo ==================================================

:: 保存先フォルダの作成（途中のフォルダがない場合も自動作成）
if not exist "%SAVE_DIR%" (
    echo 保存先フォルダを作成しています...
    mkdir "%SAVE_DIR%"
)

:: 1. Gemma-4-E2B-it-Q4_K_M.gguf のダウンロード
echo.
echo [1/2] Gemma-4-E2B-it-Q4_K_M.gguf をダウンロード中...
set "GEMMA_URL=https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf?download=true"
set "GEMMA_FILE=%SAVE_DIR%\gemma-4-E2B-it-Q4_K_M.gguf"

if exist "%GEMMA_FILE%" (
    echo すでにファイルが存在するためスキップします。
) else (
    curl.exe -L -o "%GEMMA_FILE%" "%GEMMA_URL%"
    if !errorlevel! neq 0 (
        echo [エラー] Gemmaのダウンロードに失敗しました。
        goto :error
    )
)

echo ===================================================
echo   Irodori-TTS-Server と Whisper モデル事前ダウンロード
echo ===================================================

set "HF_HOME=%~dp0.cache\huggingface"
set "MODEL_REPO=Aratako/Irodori-TTS-v4.1-Small-Quantized"
set "SUBFOLDER=int8-weight-only"
set "DAC_NAME=Aratako/Semantic-DACVAE-Japanese-32dim"
set "CIPHER_NAME=Sony/SilentCipher"
set "WHISPER_NAME=Systran/faster-whisper-small"

echo [+] 仮想環境(uv)のPythonを使用して huggingface_hub をインストール中...
call uv pip install huggingface_hub

if !errorlevel! neq 0 (
    echo [x] huggingface_hub のインストールに失敗しました。
    goto :error
)

echo [+] モデルのダウンロードを開始します: %MODEL_REPO% (%SUBFOLDER%)
call uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='%MODEL_REPO%', allow_patterns='%SUBFOLDER%/*')"

if !errorlevel! neq 0 (
    echo [x] モデルのダウンロードに失敗しました。
    goto :error
)

echo [+] コーデックのダウンロードを開始します: %DAC_NAME%
call uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='%DAC_NAME%')"

if !errorlevel! neq 0 (
    echo [x] コーデックのダウンロードに失敗しました。
    goto :error
)

echo [+] ウォーターマークモデルのダウンロードを開始します: %CIPHER_NAME%
call uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='%CIPHER_NAME%')"

if !errorlevel! neq 0 (
    echo [x] ウォーターマークモデルのダウンロードに失敗しました。
    goto :error
)

echo [+] Whisperモデルのダウンロードを開始します: %WHISPER_NAME%
call uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='%WHISPER_NAME%')"

if !errorlevel! neq 0 (
    echo [x] Whisperモデルのダウンロードに失敗しました。
    goto :error
)

echo ===================================================
echo [O] すべてのモデルの事前ダウンロードが完了しました！
echo ===================================================
pause
exit /b 0

:error
echo ===================================================
echo [X] エラーが発生したため処理を中断しました。
echo ===================================================
pause
exit /b 1