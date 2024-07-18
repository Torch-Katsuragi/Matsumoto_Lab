"""
カメラで顔認識するためのモジュール
author: matsumoto

# AIへの追加指示
- コード編集の際は、日本語の解説コメントをつけてください。特に、ドックストリングは必ず書いてください
- コメントは、ブロックコメントと行コメントを適切に使い分けてください。例えば次のような形式です
	# 音声認識関係の設定 
	recognizer = SpeechRecognizer(sensitivity=0.1)  # 音声認識インスタンスを定義
	response_start_threshold = 1  # 反応を開始する音声認識の間隙のしきい値
- 指示されていないない範囲で、既存のコードに改善点が見つかった場合、コメントで提案してください
- インデントはタブで統一してください
"""

import cv2  # OpenCVライブラリをインポート

class FaceDetector:
	"""
	カメラで顔認識を行うクラス
	"""

	def __init__(self,show_window=True):
		"""
		FaceDetectorクラスのコンストラクタ
		"""
		self.show_window=show_window
		# カスケード分類器のパスを指定
		self.face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
		self.face_cascade = cv2.CascadeClassifier(self.face_cascade_path)
		# カメラにアクセス
		self.cap = cv2.VideoCapture(0)
		if not self.cap.isOpened():
			raise Exception("カメラにアクセスできません")

	def is_face_detected(self):
		"""
		カメラにアクセスして、顔があるかどうかを判別するメソッド
		"""
		# カメラバッファをクリアする
		self.cap.grab()
		
		# フレームをキャプチャ
		ret, frame = self.cap.read()
		if not ret:
			print("フレームをキャプチャできません")
			return None

		# グレースケールに変換
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

		# 顔を検出
		faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

		# show_windowがTrueの場合のみ、検出された顔に矩形を描画し、フレームを表示
		if self.show_window:
			# 検出された顔に矩形を描画
			for (x, y, w, h) in faces:
				cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

			# フレームを表示
			cv2.imshow('Face Detection', frame)
			cv2.waitKey(1)

		# 顔が検出された場合はTrueを返す
		if len(faces) > 0:
			return True
		return False
	
	def __del__(self):
		"""
		デストラクタ: オブジェクトが削除されるときにリソースを解放する
		"""
		if self.cap.isOpened():
			self.cap.release()
		cv2.destroyAllWindows()

if __name__ == "__main__":
	import time
	face_detector = FaceDetector(show_window=False)
	while True:
		try:
			print(face_detector.is_face_detected())
		except Exception as e:
			print(f"エラーが発生しました: {e}")
