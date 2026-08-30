# SPDX-License-Identifier: CC0-1.0
#
# This work is marked with CC0 1.0 Universal. 
# To view a copy of this license, visit http://creativecommons.org

import io
import os
import sys
import time
import random
import threading
import queue
import requests
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk

# ==============================================================================
# 🛠️ 設定項目
# ==============================================================================
IMAGE_DIR = "chara1"
# IMAGE_DIR = "chara2"

IMG_FILES = {
    "eye_open_mouth_close":  "open_close.png",
    "eye_open_mouth_open":   "open_open.png",
    "eye_close_mouth_close": "close_close.png",
    "eye_close_mouth_open":  "close_open.png"
}

AUDIO_BUFFER_SIZE = 512
MOUTH_THRESHOLD = 0.02

LLAMA_SERVER_URL = "http://localhost:8080/v1/chat/completions"
IRODORI_TTS_URL  = "http://localhost:8088/v1/audio/speech"
IRODORI_VOICE    = "chara1"
# IRODORI_VOICE    = "chara2"

MAX_HISTORY_TURNS = 3
SYSTEM_PROMPT = (
    "あなたはゆうかという名前の小学生の女の子です。小学生らしい親身で楽しい会話をしましょう。"
    "感情を表すために文頭に絵文字で感情を表してください。"
    "【重要ルール】あなたは『ゆうか』のセリフだけを出力してください。自分の感情を回答に入れたり、相手の回答を作ったり、復唱したりしないでください。 "
    "1回につき、短文1文の返答だけを出力して、即座に出力を終了してください。"
    "絶対に次の行や会話を続けないでください。"
)
#SYSTEM_PROMPT = (
#    "あなたはゆうたという名前の小学生の男の子です。小学生らしい元気で楽しい話をしましょう。"
#    "感情を表すために文頭に絵文字で感情を表してください。"
#    "【重要ルール】あなたは『ゆうた』のセリフだけを出力してください。自分の感情を回答に入れたり、相手の回答を作ったり、復唱したりしないでください。 "
#    "1回につき、短文1文の返答だけを出力して、即座に出力を終了してください。"
#    "絶対に次の行や会話を続けないでください。"
#)

# ==============================================================================

# Windows環境のみ、Pythonパッケージ内のDLLパスを検索対象に追加
if sys.platform == "win32":
    import site
    user_site = site.getusersitepackages()
    global_site = site.getsitepackages()
    
    # すべてのsite-packagesディレクトリを対象にする
    for site_dir in [user_site] + global_site:
        # nvidiaパッケージ内のbinディレクトリ（DLL格納先）を探す
        nvidia_path = os.path.join(site_dir, "nvidia")
        if os.path.exists(nvidia_path):
            for sub in os.listdir(nvidia_path):
                bin_path = os.path.join(nvidia_path, sub, "bin")
                if os.path.exists(bin_path):
                    # WindowsのDLL検索パスと環境変数PATHの両方に追加
                    os.add_dll_directory(bin_path)
                    os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]

class PNGTuberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice AI Assistant")
        self.root.geometry("400x450")

        self.images = {}
        self.load_images()

        # 画像表示エリア
        self.label = tk.Label(root, image=self.images["eye_open_mouth_close"])
        self.label.pack(fill="both", expand=True)

        # GUIテキスト入力欄
        input_frame = tk.Frame(root)
        input_frame.pack(fill="x", padx=5, pady=5)

        self.entry = tk.Entry(input_frame)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.on_gui_input_submit)

        send_btn = tk.Button(input_frame, text="送信", command=self.on_gui_input_submit)
        send_btn.pack(side="right")

        # 内部状態フラグ
        self.is_eye_open = True
        self.blink_timer = 0
        self.blink_duration = 0
        self.talk_timer = 0
        self.current_volume = 0.0

        self.chat_history = []
        self.input_queue = queue.Queue()

        # アニメーション更新ループの開始
        self.update_avatar()

        # GUIが表示されたあとにスレッドを起動
        self.root.after(500, self.start_background_tasks)

    def start_background_tasks(self):
        """GUI起動完了後にバックグラウンドスレッド群を開始"""
        print("📌 [ステップ 3/4] バックグラウンドタスクを順次起動中...")

        # 音声認識スレッド起動
        self.voice_thread = threading.Thread(target=self.voice_listener_loop, daemon=True)
        self.voice_thread.start()

        # パイプラインスレッド起動
        self.pipeline_thread = threading.Thread(target=self.pipeline_worker_loop, daemon=True)
        self.pipeline_thread.start()

    def load_images(self):
        for key, filename in IMG_FILES.items():
            path = os.path.join(IMAGE_DIR, filename)
            if not os.path.exists(path):
                print(f"❌ エラー: 画像ファイルが見つかりません -> {path}", file=sys.stderr)
                img = Image.new('RGB', (400, 400), color=(200, 200, 200))
            else:
                img = Image.open(path)
            
            self.images[key] = ImageTk.PhotoImage(img.resize((400, 400)))

    def on_gui_input_submit(self, event=None):
        text = self.entry.get().strip()
        if text:
            print(f"\n💬 [GUI] 入力を検出: {text}")
            self.input_queue.put(text)
            self.entry.delete(0, tk.END)

    def manage_blinking(self):
        self.blink_timer += 15
        if self.is_eye_open:
            if self.blink_timer > random.randint(3000, 6000):
                self.is_eye_open = False
                self.blink_timer = 0
                self.blink_duration = random.randint(100, 200)
        else:
            if self.blink_timer > self.blink_duration:
                self.is_eye_open = True
                self.blink_timer = 0

    def update_avatar(self):
        self.manage_blinking()

        if self.current_volume > MOUTH_THRESHOLD:
            self.talk_timer += 15
            is_talk_frame = (self.talk_timer // 90) % 2 == 0
            is_mouth_open = is_talk_frame or (self.current_volume > MOUTH_THRESHOLD * 2.0)
        else:
            self.talk_timer = 0
            is_mouth_open = False

        if self.is_eye_open:
            key = "eye_open_mouth_open" if is_mouth_open else "eye_open_mouth_close"
        else:
            key = "eye_close_mouth_open" if is_mouth_open else "eye_close_mouth_close"

        self.label.config(image=self.images[key])
        self.root.after(15, self.update_avatar)

    def play_audio_with_lipsync(self, sample_rate, audio_data):
        # 遅延インポート（フリーズ対策）
        import sounddevice as sd

        if audio_data.dtype == np.int16:
            float_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            float_data = audio_data.astype(np.float32) / 2147483648.0
        else:
            float_data = audio_data.astype(np.float32)

        channels = 1 if float_data.ndim == 1 else float_data.shape[1]
        ANALYSIS_CHUNK_SIZE = 512

        try:
            with sd.OutputStream(samplerate=sample_rate, channels=channels, 
                                 blocksize=AUDIO_BUFFER_SIZE, dtype='float32') as stream:
                total_samples = len(float_data)
                
                for i in range(0, total_samples, ANALYSIS_CHUNK_SIZE):
                    chunk = float_data[i:i + ANALYSIS_CHUNK_SIZE]
                    rms = np.sqrt(np.mean(chunk**2)) if len(chunk) > 0 else 0.0
                    self.current_volume = rms

                    if len(chunk) < ANALYSIS_CHUNK_SIZE:
                        if channels == 1:
                            chunk = np.pad(chunk, (0, ANALYSIS_CHUNK_SIZE - len(chunk)))
                        else:
                            chunk = np.pad(chunk, ((0, ANALYSIS_CHUNK_SIZE - len(chunk)), (0, 0)))

                    stream.write(chunk)

        except Exception as e:
            print(f"❌ 音声再生エラー: {e}")
        finally:
            self.current_volume = 0.0

    def voice_listener_loop(self):
        # 重い音声認識ライブラリをサブスレッド内で遅延読み込み（フリーズ対策）
        print("🔍 [音声] speech_recognition と faster_whisper をロード中...")
        import speech_recognition as sr

        # マイクデバイスの検出とチェック
        try:
            mic_list = sr.Microphone.list_microphone_names()
            if not mic_list:
                print("⚠️ [音声] マイクが見つかりません。GUI入力モードのみで起動します。")
                return
            microphone = sr.Microphone()
            
            # ダミーでのオープンテスト
            with microphone as source:
                pass
        except (OSError, AttributeError, Exception) as e:
            print(f"⚠️ [音声] マイクデバイスを開けませんでした ({e})。")
            print("💡 GUIからのテキスト入力のみで動作を継続します。")
            return

        from faster_whisper import WhisperModel

        whisper_model = WhisperModel("small", compute_type="int8")
        print("✅ [音声] Whisperモデルロード完了")

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0
        recognizer.dynamic_energy_threshold = True

        microphone = sr.Microphone()

        with microphone as source:
            print("🎙️ [音声] 周囲の雑音を測定中...静かにしてください。")
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print("\n✨ 準備完了！マイクでの会話、または画面下のテキスト入力が可能です。\n" + "="*60)

        while True:
            try:
                with microphone as source:
                    print("🎤 音声入力待ち...")
                    try:
                        audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                        print("⚡ 音声を検出、認識処理中...")
                    except sr.WaitTimeoutError:
                        continue

                raw_data = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

                segments, info = whisper_model.transcribe(
                    audio_np, language="ja", beam_size=5,   
                    vad_filter=True, vad_parameters=dict(min_silence_duration_ms=1000)
                )
                user_text = "".join([segment.text for segment in segments]).strip()

                hallucinations = ["ご視聴ありがとうございました", "字幕：", "チャンネル登録", "視聴ありがとう"]
                for h in hallucinations:
                    if h in user_text:
                        user_text = ""
                        break

                if not user_text:
                    print("⚠️ 有効な音声文字を検出できませんでした")
                    continue

                print(f"🗣️ 音声認識成功: {user_text}")
                self.input_queue.put(user_text)

            except Exception as e:
                print(f"❌ 音声認識エラー: {e}")
                time.sleep(1)

    def pipeline_worker_loop(self):
        from scipy.io import wavfile

        while True:
            try:
                user_text = self.input_queue.get()

                print(f"\n⚙️ 処理開始 (User): {user_text}")

                max_messages = MAX_HISTORY_TURNS * 2
                recent_history = self.chat_history[-max_messages:] if self.chat_history else []
                messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history + [{"role": "user", "content": user_text}]

                print("🤖 LLMへレスポンスを要求中...")
                payload = {
                    "messages": messages_payload,
                    "temperature": 0.7,
                    "max_tokens": 512
                }

                res = requests.post(LLAMA_SERVER_URL, json=payload, timeout=30)
                if res.status_code != 200:
                    print(f"❌ llama-server エラー (Status: {res.status_code}): {res.text}")
                    self.input_queue.task_done()
                    continue

                res_json = res.json()
                ai_response = ""

                if "choices" in res_json and isinstance(res_json["choices"], list) and len(res_json["choices"]) > 0:
                    first_choice = res_json["choices"][0]
                    if "message" in first_choice and "content" in first_choice["message"]:
                        ai_response = first_choice["message"]["content"]

                if ai_response:
                    stop_tokens = [
                        "</s>", "<|im_end|>", "<|end_of_text|>", "<|end_of_turn|>",
                        "<|end|>", "<|eot_id|>", "<|im_start|>user", "<|im_start|>assistant",
                        "<|im_start|>", "|im_start|>", "User:", "Assistant:"
                    ]
                    for token in stop_tokens:
                        ai_response = ai_response.replace(token, "")
                    ai_response = ai_response.strip()

                if not ai_response:
                    print("⚠️ LLMからの返答が空でした。")
                    self.input_queue.task_done()
                    continue

                print(f"🤖 LLM返答 (AI): {ai_response}")

                self.chat_history.append({"role": "user", "content": user_text})
                self.chat_history.append({"role": "assistant", "content": ai_response})

                print("⏳ Irodori-TTSへ音声合成を要求中...")
                tts_payload = {
                    "model": "irodori-tts",
                    "input": ai_response,
                    "voice": IRODORI_VOICE,
                    "response_format": "wav",
                    "irodori": {
                         "num_steps": 6,
                         "t_schedule_mode": "sway",
                         "sway_coeff": -1.0
                    }
                }

                tts_res = requests.post(IRODORI_TTS_URL, json=tts_payload, timeout=30)
                if tts_res.status_code != 200:
                    print(f"❌ Irodori-TTS エラー (Status: {tts_res.status_code}): {tts_res.text}")
                    self.input_queue.task_done()
                    continue

                audio_buffer = io.BytesIO(tts_res.content)
                sample_rate, audio_np_data = wavfile.read(audio_buffer)

                print(f"🔊 音声再生中...")
                self.play_audio_with_lipsync(sample_rate, audio_np_data)
                print("✅ 再生完了")

                self.input_queue.task_done()

            except Exception as e:
                print(f"❌ パイプラインエラー: {e}")
                time.sleep(1)

if __name__ == "__main__":
    print("📌 [ステップ 1/4] GUIウィンドウを作成中...")
    root = tk.Tk()
    
    app = PNGTuberApp(root)
    
    print("📌 [ステップ 2/4] GUIウィンドウを強制表示中...")
    root.update()  # イベントループ前に画面を強制的に1回描画
    
    print("📌 [ステップ 4/4] イベントループを開始しました。画面が表示されます。")
    root.mainloop()
