"""Smoke test da fundação: sync parcial de uma carteira real + leitura."""
import asyncio
import os
import sys

# limita o sync para o teste ser rápido (poucas páginas)
os.environ["PORTFOLIO_SYNC_MAX_PAGES"] = os.environ.get("SMOKE_MAX_PAGES", "2")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db, session_scope  # noqa: E402
from app import models  # noqa: E402
from app.sync.portfolio import sync_owner  # noqa: E402
from app.intelligence.alerts import build_alerts  # noqa: E402
from app.ploomes.client import close_ploomes  # noqa: E402
from sqlalchemy import select  # noqa: E402


async def main(owner_id: int):
    init_db()
    print(f"== sync owner {owner_id} (parcial) ==")
    res = await sync_owner(owner_id)
    print("resultado:", res)
    with session_scope() as s:
        rows = s.scalars(
            select(models.Contact).where(models.Contact.owner_id == owner_id)
            .order_by(models.Contact.priority_score.desc()).limit(8)
        ).all()
        print(f"\n== Top {len(rows)} por prioridade ==")
        for c in rows:
            print(f"  [{c.priority_score:5.1f}] {c.name[:34]:34} | "
                  f"dias_sem={c.days_without_purchase} freq={c.buy_frequency_days} "
                  f"| cot={c.open_quotes}/{c.open_quotes_value:.0f} "
                  f"| rev12m={c.revenue_12m:.0f} | seg={c.segment_name[:18]} "
                  f"| status={c.client_status}")
        al = build_alerts(s.scalars(
            select(models.Contact).where(models.Contact.owner_id == owner_id)).all())
        print(f"\n== Alertas: {al['count']} ({al['by_kind']}) ==")
        for a in al["alerts"][:6]:
            print(f"  [{a['severity']:4}] {a['kind']:12} {a['name'][:28]:28} :: {a['title']}")
    await close_ploomes()


if __name__ == "__main__":
    oid = int(sys.argv[1]) if len(sys.argv) > 1 else 40040920
    asyncio.run(main(oid))
