import joblib, os

def test_model_exists():
    assert os.path.exists("app/price_model.joblib")

def test_model_loads():
    bundle = joblib.load("app/price_model.joblib")
    assert "model" in bundle
    assert "features" in bundle