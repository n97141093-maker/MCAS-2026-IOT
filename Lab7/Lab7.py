import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

data = np.loadtxt("Bank_Customer.csv", skiprows=1, dtype=str, delimiter=',')

'''
依上課簡報 (Data Mining: Data preprocessing) 的步驟進行前處理
欄位: 0 customer_id, 1 credit_score, 2 country, 3 gender, 4 age, 5 tenure,
      6 balance, 7 products_number, 8 credit_card, 9 active_member,
      10 estimated_salary, 11 churn
'''

# ---------- 步驟 1. Data Cleaning：檢查缺值 (簡報 p.6-12) ----------
missing = np.sum((data == "") | (data == "?"))
print("缺值數量:", missing)          # 本資料集為 0，不需補值

# ---------- 步驟 2. Attribute Subset Selection：去除無關屬性 (簡報 p.31) ----------
# customer_id 就像學號，對預測客戶是否流失沒有幫助，直接刪除
data = data[:, 1:]
# 刪除後欄位: 0 credit_score, 1 country, 2 gender, 3 age, 4 tenure, 5 balance,
#             6 products_number, 7 credit_card, 8 active_member,
#             9 estimated_salary, 10 churn

# ---------- 步驟 3. 非數值型資料轉成數值型 ----------
# gender：Female=0, Male=1
gender = (data[:, 2] == "Male").astype(float).reshape(-1, 1)
# country：One-Hot 編碼 (國家之間沒有大小順序，屬於 Nominal 屬性，簡報 p.43)
countries = np.unique(data[:, 1])                      # France, Germany, Spain
country = (data[:, 1][:, None] == countries).astype(float)

cont_names = ["credit_score", "age", "tenure", "balance",
              "products_number", "estimated_salary"]
continuous = data[:, [0, 3, 4, 5, 6, 9]].astype(float)  # 連續型數值
binary = data[:, [7, 8]].astype(float)                  # credit_card, active_member
label = data[:, 10].astype(float).reshape(-1, 1)        # churn (類別標籤)

# ---------- 步驟 4. Detect outliers：Z-Score 偵測離群值 (簡報 p.19-20) ----------
# z = (x - 平均值) / 標準差，|z| > 3 視為離群值並移除
z = (continuous - continuous.mean(axis=0)) / continuous.std(axis=0)
keep = np.all(np.abs(z) <= 3, axis=1)
for i, name in enumerate(cont_names):
    print("  %-16s 離群值 %d 筆" % (name, np.sum(np.abs(z[:, i]) > 3)))
print("移除離群值後剩下 %d / %d 筆" % (keep.sum(), len(keep)))

continuous, binary, country, gender, label = (
    continuous[keep], binary[keep], country[keep], gender[keep], label[keep])

# ---------- 步驟 5. Normalization：z-score 標準化 (簡報 p.40-41) ----------
# StandardScaler 就是 z-score normalization：v' = (v - μ) / σ
continuous = StandardScaler().fit_transform(continuous)

pre_data = np.hstack([continuous, binary, country, gender, label])
header = ",".join(cont_names + ["credit_card", "active_member"]
                  + ["country_" + c for c in countries] + ["gender", "churn"])
np.savetxt("Bank_Customer_Preprocessed.csv", pre_data, delimiter=",",
           header=header, comments="", fmt="%.6f")


from sklearn.linear_model import LogisticRegression
# 決策分類器
clf = LogisticRegression()

'''
切割 data 為 x_train, x_test, y_train, y_test
Training 70% / Testing 30% (簡報 p.46)
'''
x = pre_data[:, :-1]          # 特徵
y = pre_data[:, -1]           # 類別標籤 churn
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3)

# 使用訓練集來訓練我們的分類器
clf.fit(x_train, y_train)
# 測試資料集中進行預測
pred = clf.predict(x_test)

#print (pred) # 預測分類，即客戶是否流失
#print (y_test) # 分類
print (str(accuracy_score(pred, y_test)*100 ) + "% ")   # 預測精度
