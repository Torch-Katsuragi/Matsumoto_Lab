# 松本のラボ

このリポジトリは、私がいろいろ新しいものを試すために作りました。

リポジトリの管理としてあまり上手いやり方ではないんですが、乱立すると管理が大変だなって。

主に便利ツールとかを作る作業場として機能させるつもりです。


## セットアップ

以下の手順に従ってセットアップと実行を行ってください。

### 環境変数の設定

`.env`ファイルを作成し、`.env.sample`を参考にしてAPIキーを設定してください。

voicevox api：https://voicevox.su-shiki.com/su-shikiapis/

他は、わざわざ説明する必要はないでしょう。
   ```
   OPENAI_API_KEY=your_openai_api_key
   VOICEVOX_API_KEY=your_voicevox_api_key
   GOOGLE_APPLICATION_CREDENTIALS=path_to_your_google_credentials_json
   ```

### 環境構築

chatbotにしゃべらせたい場合、VOICEVOXを自分でインストールして、「起動」しておいてください。

ほかはsetup.ps1を参考にしてください。なにかモジュールが足りないよって言われたら自分でダウンロードして下さい


## 内容物

### tester.py

tester.pyに、成果物の実行例がまとめてあります(内容はコメントで解説)。

たとえば、以下のようなものがあります
- `agentTest()`: GPTAgentを使用して、ユーザーの入力に対して応答を生成し、音声で出力するテスト。
- `threadAgentTest()`: GPTAgentを使用して、ユーザーの入力に対して非同期で応答を生成するテスト。
- `agentConversationTest()`: 音声認識→GPT→音声合成の一連の流れをテストするスクリプト。
- `multiAgentConversationTest()`: 複数のVoiceVoxスピーカーを使用して、音声認識→GPT→音声合成のテストを行うスクリプト。
- `voicevox_web_test()`: VOICEVOXのWeb APIを使用してテキストを音声に変換するテスト関数。
- `speech_recognition_test()`: 音声認識のテスト関数。
- `parroting()`: 音声認識と音声合成のテストを行うスクリプト。喋っている途中に話しかけると中断して話し直す機能を持つ。
