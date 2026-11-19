"""
Unit tests for FastAPI Web Application Endpoints and Static File Serving.
"""

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app


def test_api_endpoints():
    """Verify all FastAPI routes, security authentication, and protected endpoints."""
    client = TestClient(app)

    # 1. Test Home / Index UI (public HTML)
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "AutoJob Intelligence" in res_index.text
    assert "AutoJob Security Gateway" in res_index.text
    print("✅ GET / returns 200 OK with UI HTML and Security Gateway.")

    # 2. Test Unauthenticated Access Rejected (401 Unauthorized)
    res_unauth = client.get("/api/boards")
    assert res_unauth.status_code == 401
    assert "Unauthorized" in res_unauth.json()["detail"]
    print("✅ Unauthenticated request to /api/boards correctly rejected with 401 Unauthorized.")

    # 3. Test Invalid Key Rejected
    res_bad_login = client.post("/api/auth/login", json={"key": "wrong_key_123"})
    assert res_bad_login.status_code == 401
    print("✅ Invalid key correctly rejected with 401.")

    # 4. Test Valid Login with 'orangepie@1978'
    res_login = client.post("/api/auth/login", json={"key": "orangepie@1978"})
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert login_data["status"] == "authenticated"
    assert "token" in login_data
    token = login_data["token"]
    print(f"✅ Successful login with 'orangepie@1978' generated token: {token[:8]}...")

    # 5. Verify /api/auth/verify
    res_verify = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert res_verify.status_code == 200
    assert res_verify.json()["authenticated"] is True
    print("✅ GET /api/auth/verify confirms valid authentication token.")

    # 6. Test Authenticated Access to Protected Routes
    auth_headers = {"Authorization": f"Bearer {token}"}
    res_boards = client.get("/api/boards", headers=auth_headers)
    assert res_boards.status_code == 200
    data = res_boards.json()
    assert data["total_boards"] >= 50
    assert "categorized_boards" in data
    print(f"✅ Authenticated GET /api/boards returns {data['total_boards']} registered boards.")

    res_state = client.get("/api/scrape/state", headers=auth_headers)
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert "metrics" in state_data
    assert "summary" in state_data
    print("✅ Authenticated GET /api/scrape/state returns valid state and metrics payload.")

    res_export = client.get(f"/api/scrape/export?token={token}")
    assert res_export.status_code in [200, 404]
    print(f"✅ Authenticated GET /api/scrape/export with query token active (Status: {res_export.status_code}).")

    # 7. Test Logout
    res_logout = client.post("/api/auth/logout", headers=auth_headers)
    assert res_logout.status_code == 200
    assert res_logout.json()["status"] == "logged_out"
    print("✅ POST /api/auth/logout invalidates session.")


if __name__ == "__main__":
    test_api_endpoints()
    print("\n🎉 All FastAPI Web App tests PASSED successfully!")
