"""
author: Matsumoto
"""


from talk.speech.google_stt import SpeechRecognizer
from talk.speech.conf import VOICEVOX_APIKEY
from talk.speech.voicevox import TextToVoiceVoxWeb
from talk.speech.speech_wrapper import VoiceVoxSpeaker,VoiceVoxWebSpeaker
import logging
import time
from talk.gpt.ai_agent import AIAgent, MultiAIAgent
from talk.gpt.gpt_fileprocess import GPTFileProcessor
import cProfile
import pstats
import io
import requests,json,pyaudio


def voicevox_web_test():
    # VOICEVOXのWeb APIを使用してテキストを音声に変換するテスト関数
    text_to_voice = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY)
    print("voicevox web ver.")
    print("発話させたい文章をキーボード入力後、Enterを押してください。")
    
    while True:
        text = input("Input: ")
        text_to_voice.put_text(text)
        print("")

def speech_recognition_test():
    # 音声認識のテスト関数
    recognizer = SpeechRecognizer()
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
            time_since_last = recognizer.get_time_since_last_recognition()
            if time_since_last is not None:
                print(f"最後に音声が認識されてからの時間: {time_since_last:.2f}秒")
            else:
                print("まだ音声が認識されていません。")





def parroting():
    """
    description: このスクリプトは、音声認識と音声合成のテストを行うためのものです。ストリーミングを意識して作ったので、喋ってる途中に話しかけると中断して話し直してくれます
    known issue: 自分のスピーカーの音を自分で拾うと、再帰的に話し続けてしまう
    """
    def respond(text):
        """
        入力へのエージェントの反応を記述
        今回はおうむ返しするだけだけど、ここにいろいろ処理書けばええんちゃう？
        """
        return text
    recognizer = SpeechRecognizer()  # 音声認識インスタンス
    text_to_voice = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY)  # VOICEVOXインスタンス
    response_start_threshold = 0.5  # 反応を開始する音声認識の間隙のしきい値
    response_decide_threshold = 5  # 反応を最後までやり切る音声認識の間隙のしきい値
    
    while True:
        if recognizer.is_timed_out(response_start_threshold):  # タイムアウト確認
            text = recognizer.get_latest_recognized()  # 最新の認識結果取得
            
            if text and text.strip(): # 反応すべきテキストがある
                logging.debug("反応開始！") 
                response=respond(text)
                text_to_voice.put_text(response)  # テキストを音声に変換
                # 完全に無音になるまで待機
                while not recognizer.is_timed_out(response_decide_threshold):
                    # logging.debug("待機中...")
                    # 再び話し始めたっぽかったら(言葉に詰まったあと再び話し始めたら)
                    if not recognizer.is_timed_out(response_start_threshold):
                        logging.debug("大変だ！また話し始めたぞ！") 
                        text_to_voice.stop_and_clear()  # 再生をやめて、キューをクリアする
                        break
                logging.debug("待機ループ脱出！") 
                
                if recognizer.is_timed_out(response_decide_threshold):
                    recognizer.reset_recognition()  # 音声認識をリセット

def speakerTest():
    speaker=VoiceVoxWebSpeaker(speaker_id=8)
    speaker.speak("こんにちは")

def agentTest():
    agent=AIAgent(speaker=VoiceVoxWebSpeaker(speaker_id=2))
    while True:
        response = agent.chat(input())
        for item in agent.pop_response():
            for key, value in item.items():
                if key=="response":
                    agent.speak(value)
                    print(value)

def threadAgentTest():
    
    agent=AIAgent(speaker=VoiceVoxWebSpeaker(speaker_id=2))
    while True:
        text=input()
        agent.stop_chat_thread()
        agent.start_chatting(text)

def agentConversationTest():
    """
    description: このスクリプトは、音声認識→GPT→音声合成のテストを行うためのものです。
    known issue: 
        - 自分のスピーカーの音を自分で拾うと、再帰的に話し続けてしまう
        - 応答が遅いことがある(たぶん、入力が上書きされるたびにGPTリクエスト送ってるせい)
        →なんか、タイミングによって変わるっぽい。サーバー側の問題説あるな、これ
        - 話してるのを遮っても止まらないし、遮るタイミングによっては似たようなこと2回しゃべる
    """

    recognizer = SpeechRecognizer()  # 音声認識インスタンス
    response_start_threshold = 1  # 反応を開始する音声認識の間隙のしきい値
    response_decide_threshold = 5  # 反応を最後までやり切る音声認識の間隙のしきい値
    # speaker=ParallelSpeaker(VoiceVoxSpeaker(speaker_id=2))
    speaker=VoiceVoxSpeaker(speaker_id=0)
    agent=AIAgent(speakers=[speaker])

    while True:
        if recognizer.is_timed_out(response_start_threshold):  # タイムアウト確認
            text = recognizer.get_latest_recognized()  # 最新の認識結果取得
            
            if text and text.strip(): # 反応すべきテキストがある
                logging.debug("反応開始！") 
                agent.start_chatting(text)
                # 完全に無音になるまで待機
                while not recognizer.is_timed_out(response_decide_threshold):
                    # logging.debug("待機中...")
                    # 再び話し始めたっぽかったら(言葉に詰まったあと再び話し始めたら)
                    if not recognizer.is_timed_out(response_start_threshold):
                        if recognizer.get_latest_recognized() != text:
                            logging.debug("大変だ！また話し始めたぞ！") 
                            speaker.interrupt()
                            agent.cancel_chatting()
                            break
                logging.debug("待機ループ脱出！") 
                
                if recognizer.is_timed_out(response_decide_threshold):
                    recognizer.reset_recognition()  # 音声認識をリセット

def multiAgentConversationTest():
    """
    description: このスクリプトは、音声認識→GPT→音声合成のテストを行うためのものです。JSONを利用して話者を増やしてます
    known issue: 
        - 自分のスピーカーの音を自分で拾うと、再帰的に話し続けてしまう
        - 応答が遅いことがある(たぶん、入力が上書きされるたびにGPTリクエスト送ってるせい)
        →なんか、タイミングによって変わるっぽい。サーバー側の問題説あるな、これ
    """

    recognizer = SpeechRecognizer(sensitivity=0.2)  # 音声認識インスタンス
    response_start_threshold = 1  # 反応を開始する音声認識の間隙のしきい値
    response_decide_threshold = 5  # 反応を最後までやり切る音声認識の間隙のしきい値
    # speaker=ParallelSpeaker(VoiceVoxSpeaker(speaker_id=2))
    # speakers=[VoiceVoxWebSpeaker(3),VoiceVoxWebSpeaker(2)]
    speakers=[VoiceVoxSpeaker(3),VoiceVoxSpeaker(2)]
    agent=MultiAIAgent(speakers=speakers)

    is_recognition_updated=False
    while True:
        time.sleep(0.01)
        if recognizer.is_timed_out(response_start_threshold):  # タイムアウト確認
            text=recognizer.get_latest_recognized()
            if text and text.strip(): # 反応すべきテキストがある
                logging.debug("反応開始！")
                for speaker in speakers:
                    speaker.interrupt()
                agent.stop_chat_thread()
                if not is_recognition_updated:
                    agent.start_chatting(text)
                else:
                    agent.update_chatting(text)
                # エージェントが話し終わるまで待機
                while not agent.end_event.is_set():
                    # logging.debug("待機中...")
                    # 再び話し始めたっぽかったら(言葉に詰まったあと再び話し始めたら)
                    if recognizer.get_latest_recognized() != text:
                        logging.debug("大変だ！また話し始めたぞ！") 
                        for speaker in speakers:
                            speaker.interrupt()
                        agent.cancel_chatting()
                        is_recognition_updated=True
                        break
                    time.sleep(0.01)
                logging.debug("待機ループ脱出！") 
                if agent.end_event.is_set():
                    recognizer.reset_recognition()  # 音声認識をリセット
                    is_recognition_updated=False

def test_gpt_file_processor():
    """
    GPTFileProcessorのテスト関数
    """

    processor = GPTFileProcessor(output_json=True)
    # filepath = "test.txt"  # テスト用のファイルを作成する必要がある
    dirpath = processor.select_directory()  # フォルダ選択ダイアログで取得
    if not dirpath:  # キャンセルされた場合
        return

    instructions = r"""
# Instructions
以下のOutput formatに従って項目を埋めること

# Output format
- 出力はJson形式で，以下のフォーマットに従ってください(空文字""はあなたが変更するところ)
{"内容の要約":"",
"自由記述枠":""}

"""

    for filepath in dirpath:
        processed_text = processor.process_file(filepath, instructions)
        if processed_text:
            print(f"ファイル: {filepath}\n{processed_text}\n")







def main():
    # ログレベルを設定
    logging.basicConfig(level=logging.DEBUG)
    # logging.basicConfig(level=logging.INFO)  # 必要に応じてINFOレベルに変更

    # 各テスト関数を呼び出す
    # speech_recognition_test()  # 音声認識のテスト
    # voicevox_web_test()  # VoiceVox Webのテスト
    # parroting()  # オウム返しのテスト(音声認識→音声合成複合)
    # agentTest()  # エージェントの基本機能のテスト (仕様変えたからもう動かないかもしれない)
    # threadAgentTest()  # スレッドを使用したエージェントのテスト
    # speakerTest()  # 音声合成ラッパーのテスト
    # agentConversationTest()  # エージェントとの音声会話テスト
    # multiAgentConversationTest()  # 複数エージェントとの音声会話テスト
    test_gpt_file_processor()  # GPTでの一括ファイル処理のテスト



if __name__ == "__main__":
    main()
