import asyncio
import os
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from backend.manager import ProxyManager

app = FastAPI(title="ProCheck - Ultra Proxy Scraper & Checker", version="2.0.0")

manager = ProxyManager(data_dir="data")

# Active WebSocket connections
active_connections: List[WebSocket] = []

class ScrapeRequest(BaseModel):
    custom_urls: Optional[List[str]] = None

class CheckRequest(BaseModel):
    concurrency: int = 150
    timeout: float = 5.0
    target_url: str = "http://httpbin.org/ip"
    custom_proxies: Optional[List[str]] = None

async def broadcast_event(event_type: str, data: dict):
    message = {"type": event_type, "data": data}
    disconnected = []
    for conn in active_connections:
        try:
            await conn.send_json(message)
        except Exception:
            disconnected.append(conn)
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "data": {
                "stats": manager.stats,
                "is_scraping": manager.is_scraping,
                "is_checking": manager.is_checking,
                "scraped_count": len(manager.scraped_proxies),
                "results_count": len(manager.results)
            }
        })
        while True:
            # Keep alive and handle client pings
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.post("/api/scrape")
async def start_scrape(req: ScrapeRequest = ScrapeRequest()):
    if manager.is_scraping:
        return {"status": "error", "message": "Scrape already in progress"}
    
    asyncio.create_task(run_scrape_task(req.custom_urls))
    return {"status": "started", "message": "Proxy scraping initiated"}

async def run_scrape_task(custom_urls: Optional[List[str]]):
    await broadcast_event("scrape_start", {})
    proxies = await manager.scrape(custom_urls=custom_urls)
    await broadcast_event("scrape_done", {
        "count": len(proxies),
        "proxies": proxies[:100]  # Preview
    })

@app.post("/api/check")
async def start_check(req: CheckRequest):
    if manager.is_checking:
        return {"status": "error", "message": "Check already in progress"}
    
    target_proxies = None
    if req.custom_proxies:
        target_proxies = []
        for line in req.custom_proxies:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                parts = line.split(":")
                ip = parts[0].strip()
                port = int(parts[1].strip())
                target_proxies.append({"ip": ip, "port": port, "protocol": "http"})
    
    asyncio.create_task(run_check_task(target_proxies, req.concurrency, req.timeout, req.target_url))
    return {"status": "started", "message": "Proxy checking initiated"}

async def run_check_task(proxies, concurrency, timeout, target_url):
    await broadcast_event("check_start", {"concurrency": concurrency, "timeout": timeout})
    
    async def progress_cb(result, stats):
        await broadcast_event("check_progress", {
            "result": result,
            "stats": stats
        })

    results = await manager.check(
        proxies=proxies,
        concurrency=concurrency,
        timeout=timeout,
        target_url=target_url,
        progress_cb=progress_cb
    )
    
    await broadcast_event("check_done", {
        "stats": manager.stats,
        "alive_total": len([r for r in results if r.get("alive")])
    })

@app.post("/api/stop")
async def stop_check():
    manager.stop_checking()
    await broadcast_event("check_stopped", {})
    return {"status": "stopped"}

@app.get("/api/status")
async def get_status():
    return {
        "is_scraping": manager.is_scraping,
        "is_checking": manager.is_checking,
        "stats": manager.stats,
        "scraped_count": len(manager.scraped_proxies),
        "results_count": len(manager.results)
    }

@app.get("/api/results")
async def get_results(
    status: str = Query("all"),      # all, alive, dead
    protocol: str = Query("all"),    # all, http, https, socks4, socks5
    search: str = Query(""),
    anonymity: str = Query("all"),   # all, Transparent, Anonymous, Elite / High
    max_latency: int = Query(10000),
    limit: int = Query(500),
    offset: int = Query(0)
):
    filtered = manager.results

    if status == "alive":
        filtered = [r for r in filtered if r.get("alive")]
    elif status == "dead":
        filtered = [r for r in filtered if not r.get("alive")]

    if protocol != "all":
        filtered = [r for r in filtered if r.get("protocol", "").lower() == protocol.lower()]

    if anonymity != "all":
        filtered = [r for r in filtered if anonymity.lower() in r.get("anonymity", "").lower()]

    if max_latency < 10000:
        filtered = [r for r in filtered if r.get("latency") and r.get("latency") <= max_latency]

    if search:
        search_lower = search.lower()
        filtered = [r for r in filtered if search_lower in r.get("proxy", "").lower() or search_lower in r.get("anonymity", "").lower()]

    total = len(filtered)
    paged = filtered[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": paged
    }

@app.get("/api/export")
async def export_proxies(
    protocol: str = Query("all"),
    format_type: str = Query("txt")  # txt, json, csv
):
    content = manager.export_formatted(protocol=protocol, format_type=format_type)
    
    media_types = {
        "txt": "text/plain",
        "json": "application/json",
        "csv": "text/csv"
    }
    
    filename = f"proxies_{protocol}_{format_type}.{format_type}"
    return Response(
        content=content,
        media_type=media_types.get(format_type, "text/plain"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# Mount static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>ProCheck API Running</h1><p>Static UI loading...</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
