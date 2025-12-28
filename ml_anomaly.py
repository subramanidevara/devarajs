import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(csv_file="attendance.csv"):
    try:
        df = pd.read_csv(csv_file)
        if df.empty:
            return []

        df["session_code"] = df["session"].map({"MORNING":0,"EVENING":1})
        df["date_num"] = pd.to_datetime(df["date"]).astype(int) // 10**9

        X = df[["date_num","session_code"]]

        model = IsolationForest(contamination=0.1, random_state=42)
        df["anomaly"] = model.fit_predict(X)

        return df[df["anomaly"]==-1].to_dict(orient="records")
    except:
        return []
