# Matsumoto Lab

個人用の実験・便利ツール置き場です。特に `talk/` 配下は「音声認識 → LLM → 音声合成」の実験コードが中心です。

## できること（ざっくり）

- **音声会話ボット**: Google Speech-to-Text で聞き取り、OpenAI API で応答生成し、VOICEVOX / AivisSpeech で読み上げ
- **GPTのファイル一括処理**: フォルダを選び、指示に沿ってファイルを処理
- **Imagen 3 画像生成（CSVバッチ）**: Vertex AI の Imagen 3 を使って t2i / i2i をまとめて生成
- **その他**: カメラ系、採点系など（実験コードが混在）

## セットアップ（Windows / PowerShell）

### 1) Python 仮想環境 + 依存関係

`setup.ps1` の手順通りでOKです。

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2) 環境変数（`.env`）

このリポジトリは `python-dotenv` により `.env` を自動読み込みします（例: `talk/speech/conf.py`）。

プロジェクト直下に `.env` を作成してください（必要なら `.env.sample` をコピーして使ってください）。

```env
# 必須（LLM）
OPENAI_API_KEY=your_openai_api_key

# 任意（VOICEVOX Web API を使う場合）
VOICEVOX_API_KEY=your_voicevox_api_key

# 任意（Google Speech-to-Text を使う場合）
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\google-credentials.json

# 任意（Imagen 3 / Vertex AI を使う場合）
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_CLOUD_LOCATION=asia-northeast2
IMAGEN3_MODEL=imagen-3.0-generate-001

# 任意（Imagen 3 / Gemini API を使う場合: Windows ARM64 等で推奨）
GOOGLE_API_KEY=your_google_api_key

# 任意（現状コードに登場するが未使用の可能性あり）
ANTHROPIC_API_KEY=your_anthropic_api_key
```

- **VOICEVOX API（Web）**: `VOICEVOX_API_KEY` は VOICEVOX の Web API を使う時に必要です（例: `talk/speech/voicevox.py` の `TextToVoiceVoxWeb`）
- **Google STT**: `GOOGLE_APPLICATION_CREDENTIALS` は Google Cloud の認証 JSON パスです（例: `talk/speech/google_stt.py`）

## 実行例

### すぐ試す（ファイル一括処理）

`tester.py` の `main()` はデフォルトで `test_gpt_file_processor()` を呼びます。

```powershell
python tester.py
```

### 音声会話（実験）

```powershell
python -m talk.chatbot
```

※ 音声周りは環境依存が強いです。まず「音声認識のみ」「音声合成のみ」を `tester.py` 内のテスト関数で個別に動作確認するのを推奨します。

### Imagen 3（CSVバッチ / t2i・i2i）

```powershell
python -m image.batch_imagen3 --csv .\path\to\jobs.csv
```

- **t2i**: `mode=t2i`、`prompt` のみ
- **i2i**: `mode=i2i`、`prompt` + `init_image_path`（入力画像パス）

引数なしで実行した場合（例: エディタの F5 実行）は、CSV をファイルダイアログから選択して実行します。

出力は **Downloads 固定**で、`generated_image\<YYYYMMDD_HHMMSS>` にまとめて保存されます。

## ディレクトリ構成（ざっくり）

- **`talk/`**: 音声会話まわり
  - **`talk/speech/`**: 音声認識・音声合成（Google STT / VOICEVOX / AivisSpeech）
  - **`talk/gpt/`**: OpenAI API とのやり取り、ストリーミング処理など
- **`image/`**: 画像生成・認識まわり（現状: Imagen 3 バッチ生成）
- **`camera/`**: カメラ系の実験（例: `face_recognition.py`）
- **`R_statistics/`**: R の実験

## Troubleshooting

- **PyAudio が入らない**: Windows は環境によって `pyaudio` の導入が詰まりがちです。`pip install pyaudio` が失敗する場合、Python のバージョンやビルド環境（MSVC）を見直してください。
- **VOICEVOX / AivisSpeech**: ローカルエンジンを使う場合は別途インストール＆起動が必要です（VOICEVOX デフォルトは `127.0.0.1:50021`、AivisSpeech は `127.0.0.1:10101` を想定したコードがあります）。
- **Google STT が動かない**: `GOOGLE_APPLICATION_CREDENTIALS` のパスと、GCP 側の API 有効化/権限を確認してください。
