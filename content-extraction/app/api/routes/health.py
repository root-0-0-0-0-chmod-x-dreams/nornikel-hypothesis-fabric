from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request) -> dict[str, object]:
    browser_pool = request.app.state.browser_pool
    try:
        await browser_pool.ensure_ready()
    except Exception:
        return {"status": "starting", "ready": False}

    ready_state = browser_pool.is_ready()
    status = "ok" if ready_state else "starting"
    return {"status": status, "ready": ready_state}
