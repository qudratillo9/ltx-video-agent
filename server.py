import os
import httpx
from mcp.server.fastmcp import FastMCP

# LTX API sozlamalari
LTX_API = "https://api.ltx.io/v2"
API_KEY = os.environ.get("LTX_API_KEY")

# Render porti
PORT = int(os.environ.get("PORT", "8000"))

# MCP server
mcp = FastMCP("LTX Video Agent")

mcp.settings.host = "0.0.0.0"
mcp.settings.port = PORT


@mcp.tool()
async def generate_video(
    prompt: str,
    duration: int = 8,
    quality: str = "fast",
    vertical: bool = True,
) -> dict:
    """Generate a video using the LTX-2.5 API."""

    if not API_KEY:
        return {"error": "LTX_API_KEY is not configured."}

    if not prompt.strip():
        return {"error": "Please provide a video prompt."}

    if len(prompt) > 5000:
        return {"error": "Prompt must not exceed 5000 characters."}

    if duration < 1 or duration > 20:
        return {"error": "Duration must be between 1 and 20 seconds."}

    if quality.lower() not in ("fast", "pro"):
        return {"error": "Quality must be fast or pro."}

    model = (
        "ltx-2-5-pro"
        if quality.lower() == "pro"
        else "ltx-2-5-fast"
    )

    resolution = "1080x1920" if vertical else "1920x1080"

    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "fps": 24,
        "generate_audio": True,
    }

    try:
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
                "error": "LTX API request failed.",
                "status_code": response.status_code,
                "details": response.text[:1500],
            }

        data = response.json()

        return {
            "message": "Video generation started.",
            "job_id": data.get("id"),
            "model": model,
            "duration": duration,
            "next_step": (
                "Call check_video_status with the returned job_id."
            ),
        }

    except httpx.HTTPError as error:
        return {"error": f"Connection error: {str(error)}"}


@mcp.tool()
async def check_video_status(job_id: str) -> dict:
    """Check a video generation job and retrieve its result."""

    if not API_KEY:
        return {"error": "LTX_API_KEY is not configured."}

    if not job_id.strip():
        return {"error": "A job_id is required."}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{LTX_API}/text-to-video/{job_id}",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                },
            )

        if response.status_code != 200:
            return {
                "error": "Could not retrieve video status.",
                "status_code": response.status_code,
                "details": response.text[:1500],
            }

        data = response.json()

        result = {
            "job_id": job_id,
            "status": data.get("status"),
        }

        if data.get("status") == "completed":
            result["video_url"] = (
                data.get("result", {}).get("video_url")
            )

        if data.get("status") == "failed":
            result["error"] = data.get("error")

        return result

    except httpx.HTTPError as error:
        return {"error": f"Connection error: {str(error)}"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")