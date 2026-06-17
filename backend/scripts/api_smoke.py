"""Smoke test da API com auth (usa TestClient, dispara lifespan)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402

OWNER = int(sys.argv[1]) if len(sys.argv) > 1 else 40040920

with TestClient(app) as c:
    print("health:", c.get("/api/health").json())
    r = c.post("/api/auth/login", json={
        "email": settings.portal_admin_email, "password": settings.portal_admin_password})
    print("login:", r.status_code)
    tok = r.json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    print("me:", c.get("/api/auth/me", headers=h).json())

    ck = c.get(f"/api/cockpit?owner_id={OWNER}&top=6", headers=h)
    print("cockpit status:", ck.status_code)
    d = ck.json()
    print("KPIs:", d["kpis"])
    print("alerts_by_kind:", d["alerts_by_kind"])
    print("\nTOP FILA:")
    for q in d["queue"]:
        print(f"  [{q['priority_score']:5.1f}] {q['name'][:32]:32} "
              f"dias={q['days_without_purchase']} freq={q['buy_frequency_days']} "
              f"cot={q['open_quotes']}/{q['open_quotes_value']:.0f} rev={q['revenue_12m']:.0f}")
    print("\nTOP ALERTAS:")
    for a in d["alerts"][:5]:
        print(f"  [{a['severity']:4}] {a['kind']:12} {a['name'][:26]:26} :: {a['title']}")
    # bloqueio de vendedor sem owner / admin sem owner_id
    print("\nadmin sem owner_id (deve 400):", c.get("/api/cockpit", headers=h).status_code)
