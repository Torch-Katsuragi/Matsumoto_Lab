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
    # SpeechRecognizerクラスのインスタンスを作成
    # これにより、音声認識機能が利用可能になる
    recognizer = SpeechRecognizer()
    
    # TextToVoiceVoxWebクラスのインスタンスを作成
    # VOICEVOX_APIKEYを使用して、テキストを音声に変換する機能を提供
    text_to_voice = TextToVoiceVoxWeb(apikey=VOICEVOX_APIKEY)
    
    # 無限ループを開始
    # このループは、音声認識とテキストの音声変換を継続的に行うために使用される
    while True:
        # 最後に音声が認識されてからの経過時間を取得
        # このメソッドは、音声認識が最後に成功してからの時間を秒単位で返す
        time_since_last = recognizer.get_time_since_last_recognition()
        
        # 音声認識がタイムアウトしたかどうかを確認
        # is_timed_outメソッドは、指定された秒数（ここでは1秒）を超えて音声が認識されていない場合にTrueを返す
        if recognizer.is_timed_out(1):
            # 最新の認識結果を取得
            # get_latest_recognizedメソッドは、認識された最新のテキストを返す
            text = recognizer.get_latest_recognized()
            
            # 取得したテキストをVOICEVOXに渡して音声に変換
            # put_textメソッドは、指定されたテキストを音声に変換するために使用される
            text_to_voice.put_text(text)
            
            # 音声認識をリセット
            # reset_recognitionメソッドは、音声認識の状態を初期化し、次の認識に備える
            recognizer.reset_recognition()
def main():
    # speech_recognition_test()
    # voicevox_web_test()
    parroting()







if __name__ == "__main__":
    main()
