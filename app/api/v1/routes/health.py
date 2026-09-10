from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def api_health() -> dict[str, str]:
    return {"status": "ok"}
