import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LTX Video Agent")

LTX_API = "https://api.ltx.io/v2"
API_KEY = os.environ.get("LTX_API_KEY")


@mcp.tool()
async def generate_video(
    prompt: str,
    duration: int = 8,
    quality: str = "fast",
    vertical: bool = True,
) -> dict:
    """Generate an AI video using LTX-2.5 from a text prompt."""

    if not API_KEY:
        return {"error": "LTX_API_KEY environment variable is missing."}

    if not prompt.strip():
        return {"error": "Please provide a video prompt."}

    if duration not in [6, 8, 10, 12, 14, 16, 18, 20]:
        return {"error": "Duration must be between 6 and 20 seconds."}

    model = (
        "ltx-2-5-pro"
        if quality.lower() == "pro"
        else "ltx-2-5-fast"
    )

    resolution = "720x1280" if vertical else "1280x720"

    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "fps": 24,
        "generate_audio": True,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{LTX_API}/text-to-video",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 202:
        return {
            "error": "LTX API request failed",
            "details": response.text,
        }

    data = response.json()

    return {
        "message": "Video generation started successfully.",
        "job_id": data["id"],
        "model": model,
        "duration": duration,
        "next_step": "Use check_video_status with this job_id.",
    }


@mcp.tool()
async def check_video_status(job_id: str) -> dict:
    """Check the generation status and retrieve the video URL when ready."""

    if not API_KEY:
        return {"error": "LTX_API_KEY environment variable is missing."}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{LTX_API}/text-to-video/{job_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    if response.status_code != 200:
        return {
            "error": "Could not retrieve video status",
            "details": response.text,
        }

    data = response.json()

    result = {
        "job_id": job_id,
        "status": data.get("status"),
    }

    if data.get("status") == "completed":
        result["video_url"] = data.get("result", {}).get("video_url")

    if data.get("status") == "failed":
        result["error"] = data.get("error")

    return result


if __name__ == "__main__":
port = int(os.environ.get(“PORT”, “8000"))
mcp.settings.port = port
mcp.run(transport=“streamable-http”)