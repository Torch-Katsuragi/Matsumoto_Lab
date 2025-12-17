"""
画像生成まわりの設定を `.env` / 環境変数から読む。

既存の `talk/speech/conf.py` と同様に python-dotenv を前提にする。
"""

from __future__ import annotations

import os

try:
    # 依存が未導入でも --help 等が動くようにする（本番では requirements.txt を入れる想定）
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ModuleNotFoundError:
    # dotenv が無くても環境変数直読みで動けるようにする
    pass


# Vertex AI（推奨: サービスアカウント + ADC）
GCP_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")
# デフォルトは大阪（asia-northeast2）
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GCP_LOCATION") or "asia-northeast2"

# 画像生成モデル名
# gemini-3-pro-image-preview: マルチモーダル入力で参照画像（最大14枚）を使った画像生成が可能
IMAGEN3_MODEL = os.environ.get("IMAGEN_MODEL") or os.environ.get("IMAGEN3_MODEL") or "gemini-3-pro-image-preview"

# Gemini API / Google GenAI（任意: API Key 方式を使いたい場合）
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


