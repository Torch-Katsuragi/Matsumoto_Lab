"""
author Matsumoto
音声認識とか音声合成とかの外部からの振舞いを統一して切り変えやすくするためのラッパ群
"""
try:
    from .voicevox import TextToVoiceVoxWeb,TextToVoiceVox
    from .conf import *
except:
    from voicevox import TextToVoiceVoxWeb,TextToVoiceVox
    from conf import *

from queue import Queue
from threading import Thread
import logging

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


# ローカルで処理
class VoiceVoxSpeaker(Speaker):
    tts = None  # 音声合成用のインスタンスをクラス変数として定義(じゃないとthreadが乱立する)

    def __init__(self, speaker_id):
        """
        VoiceVoxSpeakerの初期化メソッド。
        idはたまに更新されるので、何かおかしいと思ったらvoicevoxを起動後に以下の手順で確認
        1. http://localhost:50021/docs
        2. /core_versionsを実行
        3. 取得したバージョンを/speakersに入力してidをjsonでゲット
        ↓ ver.0.19.1 (core0.15.3)
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
        self.speaker_id = speaker_id
        # 初めてのインスタンス定義時にだけ音声合成クラスを呼び出し
        if __class__.tts is None:
            __class__.tts = TextToVoiceVox()

    def speak(self, text: str) -> None:
        """
        テキストを音声に変換して再生する。
        音声の再生か完了するまで処理は待機される

        Args:
            text (str): 音声合成対象のテキスト。
        """
        self.__class__.tts.set_speaker_id(self.speaker_id)
        self.__class__.tts.put_text(text, blocking=True)
        logging.debug("speech complete")

    def interrupt(self):
        """
        音声再生を中断し、キューをクリアする。
        """
        self.__class__.tts.stop_and_clear()  # 再生をやめて、キューをクリアする

# webで処理
class VoiceVoxWebSpeaker(VoiceVoxSpeaker):
    tts = None  # 音声合成用のインスタンスをクラス変数として定義(じゃないとthreadが乱立する)
    def __init__(self, speaker_id: int):
        """
        voicevoxをwebapiから実行
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
        
        self.speaker_id = speaker_id
        # 初めてのインスタンス定義時にだけ音声合成クラスを呼び出し
        if self.__class__.tts is None:
            self.__class__.tts = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY)

def main():
    logging.basicConfig(level=logging.DEBUG)
    zundamon = VoiceVoxSpeaker(speaker_id=3)
    metan = VoiceVoxSpeaker(speaker_id=2)
    # zundamon = VoiceVoxWebSpeaker(speaker_id=45)
    # metan = VoiceVoxWebSpeaker(speaker_id=2)

    # テスト用のテキストを追加
    zundamon.speak("こんにちは、ずんだもんなのだ")
    metan.speak("四国めたんよ")


if __name__ == "__main__":
    main()
