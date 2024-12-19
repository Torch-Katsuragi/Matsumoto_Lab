try:
    # talkパッケージ外からの参照
    from .gpt.gpt_agent import GPTAgent, MultiGPTAgent
    from .speech.speech_wrapper import VoiceVoxSpeaker, AivisSpeechSpeaker
    from .speech.google_stt import SpeechRecognizer
except ImportError:
    # 内部からの参照
    from gpt.gpt_agent import GPTAgent, MultiGPTAgent
    from speech.speech_wrapper import VoiceVoxSpeaker, AivisSpeechSpeaker
    from speech.google_stt import SpeechRecognizer

import logging
import time
import random



class ChatBot():
    def __init__(self) -> None:

        # ロギングの設定
        logging.basicConfig(level=logging.DEBUG)


        # 音声認識関係の設定
        self.recognizer = SpeechRecognizer(sensitivity=1)  # 音声認識インスタンスの生成
        self.response_start_threshold = 1  # 反応を開始する音声認識の間隙のしきい値の設定

        # スピーカーの設定
        # self.speakers=[VoiceVoxSpeaker(speaker_id=43)]  # VoiceVoxスピーカーの設定
        self.speakers=[AivisSpeechSpeaker(speaker_id=888753761),AivisSpeechSpeaker(speaker_id=888753761)]  # AivisSpeechスピーカーの設定

        # 会話モードの設定
        self.agent=MultiGPTAgent(speakers=self.speakers)
    
    def start_chatting(self) -> None:

        # 音声認識の更新フラグの初期化
        self.is_recognition_updated=False
        self.last_conversation_time=time.time()
        while True:
            time.sleep(0.01)

            # キャッシュが無限にたまると困るので、一定時間ごとに音声認識を初期化
            if time.time() - self.last_conversation_time > 240:  # 互いに無言のまま240秒経過したら
                logging.debug("最後の会話から240秒経過したのでいろいろ初期化")
                self.last_conversation_time = time.time()  # 時間を更新
                self.agent.reset()  # agentを初期化
                self.recognizer.reset_recognition()  # 音声認識をリセット
            
            # 音声認識結果 -> user_utteranceに対して処理
            if self.recognizer.is_timed_out(self.response_start_threshold):  # 最後の認識から一定市場の時間が経過したら
                user_utterance=self.recognizer.get_latest_recognized()
                gpt_input=self.handle_user_input(user_utterance) # 手動処理
                self.respond(gpt_input) # AI応答

    def respond(self,text)-> None:
        time.sleep(0.2)
        if text and text.strip():  # 反応すべきテキストが存在するかの確認
            logging.debug("反応開始！")
            # 話してる途中だったら中断する
            for speaker in self.speakers:
                speaker.interrupt()  # スピーカーの中断
            self.agent.stop_chat_thread()  # GPTスレッドの停止
            # GPTに入力を送信
            if not self.is_recognition_updated:
                # 普通の入力だったら普通に応答する
                self.agent.start_chatting(text)
            else:
                # userが割り込んできていたら割り込みモードで応答する
                self.agent.update_chatting(text)
            # エージェントが話し終わるまで待機
            while not self.agent.end_event.is_set(): 
                # 再び話し始めたっぽかったら(言葉に詰まったあと再び話し始めたら)応答を中断
                if self.recognizer.get_latest_recognized() != text:
                    logging.debug("大変だ！また話し始めたぞ！") 
                    for speaker in self.speakers:
                        speaker.interrupt()
                    self.agent.cancel_chatting()
                    self.is_recognition_updated = True
                    break
                time.sleep(0.01)
            
            logging.debug("待機ループ脱出！") 
            # (割り込まれず)最後まで話したか？
            if self.agent.end_event.is_set():
                logging.debug("agent turn end!")
                self.handle_agent_output(self.agent.get_recent_output()) # agentが話したことについて何か処理する
                self.last_conversation_time = time.time()
                self.recognizer.reset_recognition()  # 音声認識をリセット
                self.is_recognition_updated = False
    
    def handle_user_input(self,text):
        """
        userの入力から特定の処理を行う
        継承先で使うために作ったのでここでは何もしない
        """
        return text
    
    def handle_agent_output(self,text):
        """
        AIの出力テキストを処理して何かする．
        ただし，会話ログそのものは.user_data/log/に自動保存されているので，それ以外で
        継承先で使うために作ったのでここでは何もしない
        """
        pass





def main():
    bot=ChatBot()
    bot.start_chatting()

if __name__ == "__main__":
    main()