# このファイルはGoogle Cloud Speech-to-Textを使用して音声認識を行うためのモジュール+サンプルコードです。
# author: Matsumoto
# 必要なライブラリ:
# - google-cloud-speech: Google Cloud Speech-to-Text APIのクライアントライブラリ
# - pyaudio: オーディオストリームを扱うためのライブラリ
# - threading: マルチスレッド処理を行うための標準ライブラリ
# - queue: スレッド間でデータをやり取りするためのキュー
# - time: 時間管理のための標準ライブラリ
# - logging: ログを記録するための標準ライブラリ
# 
# 環境変数:
# - GOOGLE_APPLICATION_CREDENTIALS: Google Cloudの認証情報が含まれるJSONファイルのパスを設定する必要があります。
# 
# 使用方法:
# 1. 必要なライブラリをインストールします。
# 2. 環境変数GOOGLE_APPLICATION_CREDENTIALSを設定します。
# 3. スクリプトを実行します。
# 
# known issue:
# - 無音のまま放置するとエラー吐く


import os
import sys
from google.cloud import speech
import pyaudio
import threading
import queue
import time
import logging
import numpy as np


# Google Cloud Speech-to-Textの設定
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"path to json"

# オーディオ録音の設定
RATE = 16000  # サンプルレートを16000Hzに設定
CHUNK = int(RATE / 10)  # 100msごとにオーディオデータを処理するためのチャンクサイズ

class MicrophoneStream:
    """マイクロフォンからのストリーミング入力を処理するクラス"""
    def __init__(self, rate, chunk,sensitivity=1.0):
        self._rate = rate  # サンプルレート
        self._chunk = chunk  # チャンクサイズ
        self._buff = queue.Queue()  # オーディオデータを一時保存するキュー
        self.closed = True  # ストリームの開閉状態
        self.sensitivity = sensitivity

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()  # PyAudioインスタンスを作成
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,  # 16ビットの整数型でオーディオデータを扱う
            channels=1,  # モノラルで録音
            rate=self._rate,  # サンプルレートを設定
            input=True,  # 入力ストリームとして開く
            frames_per_buffer=self._chunk,  # チャンクサイズごとにオーディオデータを読み込む
            stream_callback=self._fill_buffer,  # コールバック関数を設定
        )
        self.closed = False  # ストリームを開く
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()  # ストリームを停止
        self._audio_stream.close()  # ストリームを閉じる
        self.closed = True  # ストリームの状態を閉じた状態に更新
        self._buff.put(None)  # キューにNoneを入れてジェネレータを終了させる
        self._audio_interface.terminate()  # PyAudioインスタンスを終了

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """バッファにオーディオデータを追加するコールバック関数"""
        # オーディオデータの感度を調整
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        audio_data = (audio_data * self.sensitivity).astype(np.int16)
        self._buff.put(audio_data.tobytes())
        return None, pyaudio.paContinue

    def generator(self):
        """オーディオデータのジェネレータ"""
        while not self.closed:  # ストリームが開いている間は続ける
            chunk = self._buff.get()  # キューからオーディオデータを取得
            if chunk is None:  # Noneが来たら終了
                return
            data = [chunk]

            # バッファに残っているデータをすべて取得する
            while True:
                try:
                    chunk = self._buff.get(block=False)  # ノンブロッキングでキューからデータを取得
                    if chunk is None:  # Noneが来たら終了
                        return
                    data.append(chunk)  # データをリストに追加
                except queue.Empty:  # キューが空ならループを抜ける
                    break

            yield b''.join(data)  # データのリストをバイト列に結合してyield


class SpeechRecognizer:
    def __init__(self, timeout=6,sensitivity=1.0):
        # Google Speech-to-Textクライアントの初期化
        self.client = speech.SpeechClient()  # Speech-to-Text APIのクライアントを作成
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # オーディオのエンコーディングをLINEAR16に設定
            sample_rate_hertz=RATE,  # サンプルレートを設定
            language_code="ja-JP",  # 言語コードを日本語に設定
            max_alternatives=1,  # 代替テキストの最大数を1に設定
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,  # 設定を適用
            interim_results=True  # 中間結果も取得するように設定
        )
        self.recognized_queue = queue.Queue()  # 認識結果を保存するキューを初期化
        
        self.last_recognized_time = None
        self.time_memory_lock = threading.Lock()
        self.sensitivity=sensitivity

        # ここで開始してもいいけど、外部から開始してもいいよ
        self.start_recognition()  # 音声認識ループを開始

    def start_recognition(self):
        """音声認識ループを実行するメソッド"""
        self.stop_event = threading.Event()  # 終了イベントを初期化
        self.recognition_thread = threading.Thread(target=SpeechRecognizer.recognition_loop,name="recognizer", args=(self.recognized_queue, self.client, self.streaming_config, self.stop_event, self,self.sensitivity))
        self.recognition_thread.start()
    
    def stop_recognition(self):
        """音声認識を停止するメソッド"""
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.stop_event.set()  # タイムアウトイベントをセット
            self.recognition_thread = None  # スレッドオブジェクトをクリアして次に進む。まだスレッドは動いてるけど、フラグ送ったしそのうち終了してくれるよ。

    # APIとのセッションは並列処理で実装
    # (APIの仕様上、「音声認識するたびに」実行される無限ループもどきを構築しないといけないので)
    @staticmethod
    def recognition_loop(queue, client, streaming_config, stop_event, recognizer,sensitivity):
        """
        音声認識を開始するメソッド
        認識結果は片っ端からqueueにぶち込む
        """
        with MicrophoneStream(RATE, CHUNK,sensitivity=sensitivity) as stream:  # マイクロフォンストリームを開始
            audio_generator = stream.generator()  # オーディオデータのジェネレータを取得
            requests = (speech.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)  # オーディオデータをリクエストに変換
            
            # ストリーミングの認識を開始。APIから何かが帰ってくるまで(たいてい、最初の音声認識があるまで)いったんここで待機するっぽい
            logging.debug("聞き取り開始")
            responses = client.streaming_recognize(streaming_config, requests)  # ストリーミング認識を開始

            # レスポンスを処理する
            for response in responses:  # レスポンスをイテレート (ストリーミングレスポンスがAPIから断続的に送られてくるので、実質無限ループ)
                
                # 外部から終了指示が送られてきたら即終了
                if stop_event.is_set():
                    break
                if not response.results:  # 結果がなければスキップ
                    continue
                logging.debug("なんか聞こえた！")

                # 最後に音声を認識した時刻を保存
                current_time = time.time()
                if recognizer.last_recognized_time is not None:
                    time_diff = current_time - recognizer.last_recognized_time
                    logging.debug(f"前回の認識時刻からの経過時間: {time_diff:.2f}秒")
                recognizer.last_recognized_time = current_time

                result = response.results[0]  # 最初の結果を取得
                if not result.alternatives:  # 代替テキストがなければスキップ
                    continue

                transcript = result.alternatives[0].transcript  # 代替テキストの最初のものを取得

                # 結果を出力&保存
                logging.debug(f"認識結果: {transcript}")
                queue.put(transcript)
            
            logging.debug("音声認識スレッド終了")

    def reset_recognition(self):
        """音声認識をリセットするメソッド"""
        self.stop_recognition()
        self.start_recognition()
        self.clear_recognized_queue()
        self.last_recognized_time=None

    def get_time_since_last_recognition(self):
        """最後に音声が認識されてからの時間を返すメソッド"""
        if self.last_recognized_time is None:
            return None
        return time.time() - self.last_recognized_time

    def get_latest_recognized(self):
        """recognized_queueの最新の要素を参照するメソッド"""
        if not self.recognized_queue.empty():
            return self.recognized_queue.queue[-1]
        return None

    def clear_recognized_queue(self):
        """recognized_queueの内容をクリアするメソッド"""
        self.recognized_queue.queue.clear()

    def pop_oldest_recognized(self):
        """recognized_queueの最古の要素をpopするメソッド"""
        if not self.recognized_queue.empty():
            return self.recognized_queue.get()
        return None

    def get_all_recognized(self):
        """recognized_queueの全ての要素をリストとして取得するメソッド"""
        return list(self.recognized_queue.queue)
    
    def is_timed_out(self, timeout):
        """最後に音声が認識されてからの時間がタイムアウト時間を超えたかどうかを返すメソッド"""
        time_since_last = self.get_time_since_last_recognition()
        if time_since_last is None:
            return False
        return time_since_last > timeout

# テストコード
def console_input_handler(recognizer):
    while True:
        user_input = input("コマンドを入力してください: ")
        
        # "参照"コマンドの処理
        if "参照" in user_input:
            latest_recognized = recognizer.get_latest_recognized()
            if latest_recognized:
                print(f"最新の認識結果: {latest_recognized}")
            else:
                print("認識結果がありません。")
        
        # "リセット"コマンドの処理
        elif "リセット" in user_input:
            recognizer.reset_recognition()
            print("音声認識を初期化しました。")
        
        # "時刻"コマンドの処理
        elif "時刻" in user_input:
            time_since_last = recognizer.time_since_last_recognition()
            if time_since_last is not None:
                print(f"最後に音声が認識されてからの時間: {time_since_last:.2f}秒")
            else:
                print("まだ音声が認識されていません。")


def main():
    recognizer=SpeechRecognizer()
    print("mainloopにただいま")
    # debugがうるさかったらinfoに変えてください
    logging.basicConfig(level=logging.DEBUG)
    # logging.basicConfig(level=logging.INFO)

    console_input_handler(recognizer)
    








if __name__ == "__main__":
    main()
