# https://github.com/AkariGroup/akari_chatgpt_bot.git
import io
import json
import time
import wave
from queue import Queue
from threading import Thread
from typing import Any

import pyaudio
import requests
import logging

try:
    from .err_handler import ignoreStderr
except:
    from err_handler import ignoreStderr

class TextToVoiceVox(object):
    """
    VoiceVoxを使用してテキストから音声を生成するクラス。
    """

    def __init__(self, host: str = "127.0.0.1", port: str = "50021", speaker_id:int=8) -> None:
        """クラスの初期化メソッド。
        Args:
            host (str, optional): VoiceVoxサーバーのホスト名。デフォルトは "127.0.0.1"。
            port (str, optional): VoiceVoxサーバーのポート番号。デフォルトは "52001"。

        """
        self.queue: Queue[str] = Queue()
        self.host = host
        self.port = port
        self.play_flg = False
        self.finished = True
        self.voice_thread = Thread(target=self.text_to_voice_thread,name="speaker")
        self.voice_thread.start()
        self.set_speaker_id(speaker_id)

    def set_speaker_id(self,id):
        self.speaker_id=id

    def __exit__(self) -> None:
        """音声合成スレッドを終了する。"""
        self.voice_thread.join()

    def text_to_voice_thread(self) -> None:
        """
        音声合成スレッドの実行関数。
        キューからテキストを取り出し、text_to_voice関数を呼び出す。

        """
        while True:
            if self.queue.qsize() > 0:
                text = self.queue.get()
                self.text_to_voice(text)
            if self.queue.qsize() == 0:
                self.finished = True
            time.sleep(0.01)
    

    def allow_speech(self):
        self.play_flg=True

    def stop_and_clear(self) -> None:
        """
        キューをクリアし、音声の再生を直ちに取りやめる。
        """
        logging.debug(f"interrupted in {self.__class__.__name__}.stop_and_clear")
        self.queue.queue.clear()  # キューをクリア
        self.play_flg = False  # 再生フラグをFalseに設定(再生中なら即ループ脱出)

    def set_speaker_id(self,id):
        """
        話者idをセット
        """
        self.speaker_id=id

    def put_text(
        self, text: str, play_now: bool = True, blocking: bool = False
    ) -> None:
        """
        音声合成のためのテキストをキューに追加する。

        Args:
            text (str): 音声合成対象のテキスト。
            play_now (bool, optional): すぐに音声再生を開始するかどうか。デフォルトはTrue。
            blocking (bool, optional): 音声合成が完了するまでブロックするかどうか。デフォルトはFalse。

        """
        if play_now:
            self.play_flg = True
        self.queue.put(text)
        self.finished = False
        if blocking:
            self.wait_finish()

    def wait_finish(self) -> None:
        """
        音声合成が完了するまで待機するループ関数。

        """
        while not self.finished:
            time.sleep(0.01)

    def post_audio_query(
        self,
        text: str,
        speaker:int=8,
        speed_scale: float = 1.0,
    ) -> Any:
        """VoiceVoxサーバーに音声合成クエリを送信する。

        Args:
            text (str): 音声合成対象のテキスト。
            speaker (int, optional): VoiceVoxの話者番号。デフォルトは8(春日部つむぎ)。
            speed_scale (float, optional): 音声の再生速度スケール。デフォルトは1.0。

        Returns:
            Any: 音声合成クエリの応答。

        """
        params = {
            "text": text,
            "speaker": self.speaker_id,
            "speed_scale": speed_scale,
            "pre_phoneme_length": 0,
            "post_phoneme_length": 0,
        }
        address = "http://" + self.host + ":" + self.port + "/audio_query"
        logging.debug(f"Address: {address}")
        res = requests.post(address, params=params)
        return res.json()

    def post_synthesis(
        self,
        audio_query_response: dict,
    ) -> bytes:
        """
        VoiceVoxサーバーに音声合成要求を送信し、合成された音声データを取得する。

        Args:
            audio_query_response (dict): 音声合成クエリの応答。

        Returns:
            bytes: 合成された音声データ。
        """
        params = {"speaker": self.speaker_id}
        headers = {"content-type": "application/json"}
        audio_query_response_json = json.dumps(audio_query_response)
        address = "http://" + self.host + ":" + self.port + "/synthesis"
        res = requests.post(
            address, data=audio_query_response_json, params=params, headers=headers
        )
        return res.content

    def play_wav(self, wav_file: bytes) -> None:
        """合成された音声データを再生する。

        Args:
            wav_file (bytes): 合成された音声データ。

        """
        wr: wave.Wave_read = wave.open(io.BytesIO(wav_file))
        with ignoreStderr():
            p = pyaudio.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(wr.getsampwidth()),
                channels=wr.getnchannels(),
                rate=wr.getframerate(),
                # rate=24000,
                output=True,
            )
            chunk = 1024
            data = wr.readframes(chunk)
            while data:
                if self.play_flg is False:
                    logging.debug("speech interrupted")
                    break
                stream.write(data)
                data = wr.readframes(chunk)
            time.sleep(0.2)
            stream.close()
        p.terminate()

    def text_to_voice(self, text: str) -> None:
        """
        テキストから音声を合成して再生する。

        Args:
            text (str): 音声合成対象のテキスト。

        """
        res = self.post_audio_query(text)
        wav = self.post_synthesis(res)
        self.play_wav(wav)


class TextToVoiceVoxWeb(TextToVoiceVox):
    """
    VoiceVox(web版)を使用してテキストから音声を生成するクラス。
    """

    def __init__(self, apikey: str,speaker_id=8) -> None:
        """クラスの初期化メソッド。
        Args:
            apikey (str): VoiceVox wweb版のAPIキー。

        """
        self.queue: Queue[str] = Queue()
        self.apikey = apikey
        self.play_flg = False
        self.voice_thread = Thread(target=self.text_to_voice_thread,name="speaker")
        self.voice_thread.start()
        self.speaker_id=speaker_id

    # def text_to_voice_thread(self) -> None:
    #     """
    #     音声合成スレッドの実行関数。
    #     キューからテキストを取り出し、text_to_voice関数を呼び出す。

    #     """
    #     while True:
    #         if self.queue.qsize() > 0 and self.play_flg:
    #             text = self.queue.get()
    #             self.text_to_voice(text)

    def post_web(
        self,
        text: str,
        speaker: int = 8,
        pitch: int = 0,
        intonation_scale: int = 1,
        speed: int = 1,
    ) -> bytes:
        """
        VoiceVoxウェブAPIに音声合成要求を送信し、合成された音声データを取得。

        Args:
            text (str): 音声合成対象のテキスト。
            speaker (int, optional): VoiceVoxの話者番号。デフォルトは8(春日部つむぎ)。
            pitch (int, optional): ピッチ。デフォルトは0。
            intonation_scale (int, optional): イントネーションスケール。デフォルトは1。
            speed (int, optional): 音声の速度。デフォルトは1。

        Returns:
            bytes: 合成された音声データ。

        """
        address = (
            "https://deprecatedapis.tts.quest/v2/voicevox/audio/?key="
            + self.apikey
            + "&speaker="
            + str(self.speaker_id)
            + "&pitch="
            + str(pitch)
            + "&intonationScale="
            + str(intonation_scale)
            + "&speed="
            + str(speed)
            + "&text="
            + text
        )
        res = requests.post(address)
        return res.content

    def text_to_voice(self, text: str) -> None:
        """
        テキストから音声を合成して再生する。

        Args:
            text (str): 音声合成対象のテキスト。

        """
        
        logging.debug("Speech synthesis requested")
        wav = self.post_web(text=text)
        logging.debug("Received WAV file")
        if self.queue.qsize() > 0:
            logging.debug("Speech synthesis canceled")
            return
        self.play_wav(wav)







def main():
    logging.basicConfig(level=logging.DEBUG)
    text_to_voice = TextToVoiceVox(speaker_id=8)

    text_to_voice.put_text("こんにちは")

if __name__ == "__main__":
    main()
