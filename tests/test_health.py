from app.app import app

def test_health():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200