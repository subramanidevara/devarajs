import pandas as pd
from sklearn.cluster import KMeans

def detect_proxy(csv_file="attendance.csv"):
    try:
        df = pd.read_csv(csv_file)
        if len(df) < 5:
            return []

        df["date_num"] = pd.to_datetime(df["date"]).astype(int) // 10**9
        X = df[["date_num"]]

        kmeans = KMeans(n_clusters=2, random_state=42)
        df["cluster"] = kmeans.fit_predict(X)

        suspicious = df.groupby("usn").filter(lambda x: len(x) > 3)
        return suspicious.to_dict(orient="records")
    except:
        return []
