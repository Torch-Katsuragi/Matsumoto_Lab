# R言語のテストコード例
# サンプルデータの作成
data <- data.frame(
  x = rnorm(100),  # 正規分布に従うランダムな数値
  y = rnorm(100)   # 正規分布に従うランダムな数値
)

# 散布図の描画
plot(data$x, data$y, main = "散布図", xlab = "X軸", ylab = "Y軸", col = "blue", pch = 19)

# 線形回帰モデルの作成
model <- lm(y ~ x, data = data)

# 回帰直線の追加
abline(model, col = "red")

# モデルの要約
summary(model)
