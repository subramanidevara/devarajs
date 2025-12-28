import pandas as pd
from sklearn.linear_model import LogisticRegression

def predict_absentee(csv_file="attendance.csv"):
    try:
        df = pd.read_csv(csv_file)
        counts = df.groupby("usn").size().reset_index(name="count")

        X = counts[["count"]]
        y = (counts["count"] < 5).astype(int)

        model = LogisticRegression()
        model.fit(X, y)

        counts["risk"] = model.predict(X)
        return counts.to_dict(orient="records")
    except:
        return []
