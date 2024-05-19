"""
author Matsumoto
音声認識とか音声合成とかの外部からの振舞いを統一して切り変えやすくするためのラッパ群
"""
try:
    from .voicevox import TextToVoiceVoxWeb
    from .conf import *
except:
    from voicevox import TextToVoiceVoxWeb
    from conf import *

from queue import Queue
from threading import Thread

class Speaker:
    def speak(self, text: str) -> None:
        """
        テキストを音声に変換して再生する。

        Args:
            text (str): 音声合成対象のテキスト。
        """
        print(text)

    def interrupt(self):
        """
        音声再生を中断する。
        """
        pass


class VoiceVoxSpeaker(Speaker):
    def __init__(self, speaker_id):
        """
        VoiceVoxSpeakerの初期化メソッド。
        子供っぽい路線で攻めるなら、0,3,28,45あたり？
        | キャラクター名 | 表情 | speaker_id |
        | --- | --- | --- |
        | 四国めたん | ノーマル | 2 |
        | 四国めたん | あまあま | 0 |
        | 四国めたん | ツンツン | 6 |
        | 四国めたん | セクシー | 4 |
        | 四国めたん | ささやき | 36 |
        | 四国めたん | ヒソヒソ | 37 |
        | ずんだもん | ノーマル | 3 |
        | ずんだもん | あまあま | 1 |
        | ずんだもん | ツンツン | 7 |
        | ずんだもん | セクシー | 5 |
        | ずんだもん | ささやき | 22 |
        | ずんだもん | ヒソヒソ | 38 |
        | ずんだもん | ヘロヘロ | 75 |
        | ずんだもん | なみだめ | 76 |
        | 春日部つむぎ | ノーマル | 8 |
        | 雨晴はう | ノーマル | 10 |
        | 波音リツ | ノーマル | 9 |
        | 波音リツ | クイーン | 65 |
        | 玄野武宏 | ノーマル | 11 |
        | 玄野武宏 | 喜び | 39 |
        | 玄野武宏 | ツンギレ | 40 |
        | 玄野武宏 | 悲しみ | 41 |
        | 白上虎太郎 | ふつう | 12 |
        | 白上虎太郎 | わーい | 32 |
        | 白上虎太郎 | びくびく | 33 |
        | 白上虎太郎 | おこ | 34 |
        | 白上虎太郎 | びえーん | 35 |
        | 青山龍星 | ノーマル | 13 |
        | 青山龍星 | 熱血 | 81 |
        | 青山龍星 | 不機嫌 | 82 |
        | 青山龍星 | 喜び | 83 |
        | 青山龍星 | しっとり | 84 |
        | 青山龍星 | かなしみ | 85 |
        | 青山龍星 | 囁き | 86 |
        | 冥鳴ひまり | ノーマル | 14 |
        | 九州そら | ノーマル | 16 |
        | 九州そら | あまあま | 15 |
        | 九州そら | ツンツン | 18 |
        | 九州そら | セクシー | 17 |
        | 九州そら | ささやき | 19 |
        | もち子さん | ノーマル | 20 |
        | もち子さん | セクシー／あん子 | 66 |
        | もち子さん | 泣き | 77 |
        | もち子さん | 怒り | 78 |
        | もち子さん | 喜び | 79 |
        | もち子さん | のんびり | 80 |
        | 剣崎雌雄 | ノーマル | 21 |
        | WhiteCUL | ノーマル | 23 |
        | WhiteCUL | たのしい | 24 |
        | WhiteCUL | かなしい | 25 |
        | WhiteCUL | びえーん | 26 |
        | 後鬼 | 人間ver. | 27 |
        | 後鬼 | ぬいぐるみver. | 28 |
        | No.7 | ノーマル | 29 |
        | No.7 | アナウンス | 30 |
        | No.7 | 読み聞かせ | 31 |
        | ちび式じい | ノーマル | 42 |
        | 櫻歌ミコ | ノーマル | 43 |
        | 櫻歌ミコ | 第二形態 | 44 |
        | 櫻歌ミコ | ロリ | 45 |
        | 小夜/SAYO | ノーマル | 46 |
        | ナースロボ＿タイプＴ | ノーマル | 47 |
        | ナースロボ＿タイプＴ | 楽々 | 48 |
        | ナースロボ＿タイプＴ | 恐怖 | 49 |
        | ナースロボ＿タイプＴ | 内緒話 | 50 |
        | †聖騎士 紅桜† | ノーマル | 51 |
        | 雀松朱司 | ノーマル | 52 |
        """
        self.tts = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY,speaker_id=speaker_id)
        self.speaker_id=speaker_id

    def speak(self, text: str) -> None:
        """
        テキストを音声に変換して再生する。

        Args:
            text (str): 音声合成対象のテキスト。
        """
        self.tts.put_text(text)

    def interrupt(self):
        """
        音声再生を中断し、キューをクリアする。
        """
        self.tts.stop_and_clear()  # 再生をやめて、キューをクリアする


class ParallelSpeaker:
    """Speakerをラップして並列処理を可能にするクラス"""
    def __init__(self, speaker: Speaker):
        """
        ParallelSpeakerの初期化メソッド。

        Args:
            speaker (Speaker): 再生に使用するSpeakerオブジェクト。
        """
        self.speaker = speaker
        self.queue = Queue()
        self.playing = False
        self.thread = Thread(target=self._play_from_queue)
        self.thread.start()

    def _play_from_queue(self):
        """
        キューからテキストを取り出して再生する内部メソッド。
        """
        while True:
            if not self.queue.empty() and not self.playing:
                text = self.queue.get()
                self.playing = True
                self.speaker.speak(text)
                self.playing = False

    def speak(self, text: str):
        """
        再生キューにテキストを追加する。

        Args:
            text (str): 再生するテキスト。
        """
        self.queue.put(text)

    def interrupt(self):
        """
        再生を中断し、キューをクリアする。
        """
        self.speaker.interrupt()
        self.queue.queue.clear()
        self.playing = False


def main():
    speaker = VoiceVoxSpeaker(speaker_id=8)
    parallel_speaker = ParallelSpeaker(speaker)

    # テスト用のテキストを追加
    parallel_speaker.speak("こんにちは、これはテストメッセージです。")
    parallel_speaker.speak("もう一つのメッセージを追加します。")

    # 再生を少し待つ
    import time
    time.sleep(10)

    # 再生を中断してキューをクリア
    parallel_speaker.interrupt()

if __name__ == "__main__":
    main()
