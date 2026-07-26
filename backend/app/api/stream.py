import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.energyplus.streamer import SimulationStreamer, create_streamer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])

_streamers: dict[str, SimulationStreamer] = {}


@router.post("/simulation/start-stream")
async def start_simulation_stream(request: dict) -> dict:
    output_dir = request.get("output_dir", "/mnt/c/EnergentOutput")
    run_id = f"run_{int(asyncio.get_event_loop().time() * 1000)}"

    streamer = await create_streamer(output_dir, poll_interval=1.0)
    _streamers[run_id] = streamer

    logger.info("Started simulation stream: %s", run_id)
    return {"run_id": run_id, "status": "started"}


@router.get("/simulation/stream/{run_id}")
async def stream_simulation_metrics(run_id: str):
    if run_id not in _streamers:
        raise HTTPException(status_code=404, detail="Stream not found")

    streamer = _streamers[run_id]

    async def event_generator():
        try:
            async for metrics in streamer.stream_metrics():
                data = json.dumps(metrics)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            logger.info("Stream cancelled for %s", run_id)
        finally:
            streamer.stop()
            _streamers.pop(run_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/simulation/stop-stream/{run_id}")
async def stop_simulation_stream(run_id: str) -> dict:
    if run_id in _streamers:
        _streamers[run_id].stop()
        _streamers.pop(run_id, None)
        return {"status": "stopped", "run_id": run_id}
    raise HTTPException(status_code=404, detail="Stream not found")