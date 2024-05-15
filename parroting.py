from lib.google_stt import SpeechRecognizer
from lib.conf import VOICEVOX_APIKEY
from lib.voicevox import TextToVoiceVoxWeb







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
    # 音声認識とVOICEVOXを組み合わせたオウム返し
    recognizer = SpeechRecognizer()
    text_to_voice = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY)
    
    while True:
        time_since_last = recognizer.get_time_since_last_recognition()
        if recognizer.is_timed_out(1):
            text=recognizer.get_latest_recognized()
            text_to_voice.put_text(text)
            recognizer.reset_recognition()

def main():
    # speech_recognition_test()
    # voicevox_web_test()
    parroting()







if __name__ == "__main__":
    main()
