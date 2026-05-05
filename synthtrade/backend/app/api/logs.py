import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/logs", tags=["logs"])

CSV_FIELDS = ["id", "strategy_id", "action", "price", "quantity", "reason", "ai_score", "created_at"]


@router.get("/export")
def export_logs(_user: str = Depends(get_current_user)):
    db = get_supabase()
    data = (db.table("operation_logs")
             .select(",".join(CSV_FIELDS))
             .order("created_at", desc=True)
             .execute()).data or []

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logs.csv"},
    )


@router.get("")
def list_logs(
    action: str | None = None,
    strategy_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: str = Depends(get_current_user),
):
    db = get_supabase()
    query = db.table("operation_logs").select("*")

    if action:
        query = query.eq("action", action)
    if strategy_id:
        query = query.eq("strategy_id", strategy_id)

    data = (query
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()).data or []

    return data
