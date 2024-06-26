# https://github.com/AkariGroup/akari_chatgpt_bot.git
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_APIKEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_APIKEY = os.environ.get("ANTHROPIC_API_KEY")
VOICEVOX_APIKEY = os.environ.get("VOICEVOX_API_KEY")
