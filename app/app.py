from flask import Flask, request, render_template, jsonify
import os
import joblib
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "price_model.joblib")
DEMO_PATH  = os.path.join(BASE_DIR, "demo_data.csv")

bundle   = joblib.load(MODEL_PATH)
model    = bundle["model"]
features = bundle["features"]

ACTUAL_COL = "ActualPrice"
demo = pd.read_csv(DEMO_PATH)

def label_for_row(i, row):
    actual = row.get(ACTUAL_COL, None)
    actual_txt = f"${actual:,.0f}" if pd.notna(actual) else "N/A"
    return f"Row {i} | Actual: {actual_txt}"

demo_options = [(int(i), label_for_row(i, r)) for i, r in demo.iterrows()]

app = Flask(__name__, template_folder="templates") 

@app.get("/health")
def health():
    return jsonify(status="ok", items=len(demo), features=len(features)), 200

@app.route("/", methods=["GET", "POST"])
def home():
    prediction   = None
    actual       = None
    demo_index   = None
    selected_row = None

    if request.method == "POST":
        val = request.form.get("demo_index", "")
        if val != "":
            demo_index = int(val)
            row = demo.loc[demo_index]
            X   = pd.DataFrame([row[features]])
            prediction = float(model.predict(X)[0])
            actual     = float(row[ACTUAL_COL]) if pd.notna(row[ACTUAL_COL]) else None
            selected_row = {k: row.get(k, None) for k in features}

    return render_template(
        "index.html",
        demo_options=demo_options,
        demo_index=demo_index,
        prediction=prediction,
        actual=actual,
        selected_row=selected_row,
        features=features,
    )

if __name__ == "__main__":
 
    app.run(host="0.0.0.0", port=5000)