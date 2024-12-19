"""
会話を通して日記を完成させるChatBotを作る

しばらく凍結．先にchatbot.pyを作って，chatbotクラスを継承する形で作るように変更する
日記作成支援の方式もGUIベースに変えて，実際に出来上がっている現在の日記(GPT側では辞書として処理)を見ながら質問していく感じにしたい
"""


from gpt.gpt_agent import GPTAgent, MultiGPTAgent
from speech.speech_wrapper import VoiceVoxSpeaker, Speaker, VoiceVoxWebSpeaker,AivisSpeechSpeaker
from speech.google_stt import SpeechRecognizer
from gpt.gpt_handler import JsonGPTHandler



import logging
import time
import random


# Namida0Homeの振舞いを定義
class DiaryMaker(MultiGPTAgent):
    
    def init_GPT(self):
        """
        GPTの初期設定を行うメソッド
        """
        self.model = "gpt-4o"  # 使用するGPTモデルを設定
        self.gpt_handler = JsonGPTHandler()  # GPTハンドラーを初期化

        self.instruction = f"""
# Instruction
あなたは，日記制作支援AI"{self.name}"です．後述するルールに従い，userから話を聞き出して日記(行動ログ)を作成してください．

- 起床時刻から現在(またはその日の就寝時刻)に至るまでの行動を隙間なく明らかにするよう試みる
- 一度に話す内容は短文にとどめる
- 聞き役に徹する
- 質問により，行動に関する詳細な情報を明らかにする
- 質問により，全ての行動について開始時間と終了時間を明確にする(15分刻み．例：16時から16時45分まで)
- 敬語は使わず、友人として接する
- 仕事や趣味の話については特に，5W1Hを基準に深堀する
- 話題がひと段落したら、次の話題に移行する
- userの事はuserとは呼ばず，"ユーザー"と呼ぶ

# Diary contents
日記は，その時々の行動により構成されます．あなたは各行動について，自明である場合を除き以下を明らかにする必要があります．
- その行動が何時から何時まで，どこで行われたか
- なぜその行動をとったのか
- その行動の結果はどうなったのか

# Circumstance
- 現在、{time.strftime('%Y年%m月%d日 %H:%M')}
"""
        if self.profile is None:
            self.profile = f"""
"""
        self.io_format = """
# Input format
入力はuserの発話を音声認識してテキスト化したものです。
音声認識は、あなたの出力の途中で更新されることがあります。その場合は、入力の最初に"updated: "の文字列を付加します

# Output format
- 出力はJSON形式で、以下のフォーマットに従ってください。
{"log": "", "あなたの名前": "ここに、あなたのuserへの言葉を入れる"}
- 入力が前回の入力を更新したものであった場合("updated: "が付加されていた場合)、それは前回のuserの入力に、前回のあなたの出力への返事を加えたものです。
    前回のあなたの出力がuserに届いているのを前提に、前回とは異なる内容を返してください

# Example (名前が"アイ"の場合)
user: やあ
assistant: {"log": "", "アイ": "やっほー、ユーザー。元気にしてた？"}
user: 元気だよ
assistant: {"log": "", "アイ": "それは良かった。今日は〇月×日だけど、今日の日記をつけたいの？"}
user: updated: やあ昨日の日記をつけたい
※ このとき、"昨日の日記をつけたい"は"今日の日記をつけたいの？"に対する返事なので、それを踏まえた回答をする
assistant: {"log": "", "アイ": "じゃあまず、昨日の起床時間から教えて！"}
user: 7時に起きたよ
assistant: {"log": "07:00 起床", "アイ": "早起きだね！その後は何をしたのか教えて！"}
user: 家で朝ごはんを食べたよ
assistant: {"log": "07:00- 自宅にて朝食", "アイ": "朝ごはんは何を食べたの？"}
user: トーストとコーヒー
assistant: {"log": "07:00- 自宅にて朝食としてトースト・コーヒーを摂る", "アイ": "美味しそうだね！朝ごはんを食べ終わったのは何時？"}
user: 8時．それから家を出たよ
assistant: {"log": "08:00 家を出る", "アイ": "お出かけしたんだね！どこに行ったのか教えて！"}
user: 会社に行ったよ
assistant: {"log": "08:00- 会社に向かう", "アイ": "お仕事お疲れ様！会社には何時に着いたの？"}
user: 8時半に着いたよ
assistant: {"log": "08:30 会社到着", "アイ": "通勤時間はちょうどいい感じだね！その後は何をしたの？"}
user: 会議があったよ
assistant: {"log": "08:30- 会議", "アイ": "会議は何時から何時までだったの？"}
user: 9時から10時まで
assistant: {"log": "09:00-10:00 会議", "アイ": "なるほど、会議の内容はどんな感じだったの？"}


"""
        # キャラクター設定を結合
        personality = self.instruction + self.profile + self.io_format
        self.characters=[self.name]
        logging.info("キャラ設定\n" + personality)  # キャラクター設定をログに出力
        self.personality_message = [{'role': 'system', 'content': personality}]  # キャラクター設定をシステムメッセージとして保存

    def save_dialog(self):
        """
        現在の会話ログを.txtファイルに保存するメソッド
        """
        super().save_dialog("DiaryDialog")




def main():
    # ロギングの設定
    logging.basicConfig(level=logging.DEBUG)


    # 音声認識関係の設定
    recognizer = SpeechRecognizer(sensitivity=1)  # 音声認識インスタンスの生成
    response_start_threshold = 1  # 反応を開始する音声認識の間隙のしきい値の設定
    

    # スピーカーの設定
    # speakers=[VoiceVoxSpeaker(speaker_id=43)]  # VoiceVoxスピーカーの設定
    speakers=[AivisSpeechSpeaker(speaker_id=888753761)]  # AivisSpeechスピーカーの設定
    # 会話モードの設定
    agent=DiaryMaker(speakers=speakers)


    # 音声認識の更新フラグの初期化
    is_recognition_updated=False
    last_conversation_time=time.time()
    while True:
        time.sleep(0.01)

        # キャッシュが無限にたまると困るので、一定時間ごとに初期化
        if time.time() - last_conversation_time > 240:  # 互いに無言のまま240秒経過したら
            logging.debug("最後の会話から240秒経過したのでいろいろ初期化")
            last_conversation_time = time.time()  # 時間を更新
            agent.reset()  # agentを初期化
            recognizer.reset_recognition()  # 音声認識をリセット
        

        if recognizer.is_timed_out(response_start_threshold):  # タイムアウトの確認
            text=recognizer.get_latest_recognized()
            time.sleep(0.2)
            if text and text.strip():  # 反応すべきテキストが存在するかの確認
                logging.debug("反応開始！")
                # 話してる途中だったら中断する
                for speaker in speakers:
                    speaker.interrupt()  # スピーカーの中断
                agent.stop_chat_thread()  # GPTスレッドの停止
                # GPTに入力を送信
                if not is_recognition_updated:
                    # 普通の入力だったら普通に応答する
                    agent.start_chatting(text)
                else:
                    # userが割り込んできていたら割り込みモードで応答する
                    agent.update_chatting(text)
                # エージェントが話し終わるまで待機
                while not agent.end_event.is_set(): 
                    # 再び話し始めたっぽかったら(言葉に詰まったあと再び話し始めたら)応答を中断
                    if recognizer.get_latest_recognized() != text:
                        logging.debug("大変だ！また話し始めたぞ！") 
                        for speaker in speakers:
                            speaker.interrupt()
                        agent.cancel_chatting()
                        is_recognition_updated=True
                        break
                    time.sleep(0.01)
                
                logging.debug("待機ループ脱出！") 
                # (割り込まれず)最後まで話したか？
                if agent.end_event.is_set():
                    logging.debug("agent turn end!")
                    last_conversation_time=time.time()
                    recognizer.reset_recognition()  # 音声認識をリセット
                    is_recognition_updated=False




if __name__ == "__main__":
    main()
