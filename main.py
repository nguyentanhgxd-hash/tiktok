import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

# Cho phép Blogger gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/download")
def download_media(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Không có tiêu đề')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration_string', 'N/A')
            
            formats_list = []
            formats = info.get('formats', [info])
            
            for f in formats:
                if f.get('url'):
                    formats_list.append({
                        'quality': f.get('format_note') or f.get('resolution') or 'HD',
                        'ext': f.get('ext', 'mp4'),
                        'url': f.get('url')
                    })
            
            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "formats": formats_list[:3]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/proxy-download")
async def proxy_download(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/"
    }
    try:
        client = httpx.AsyncClient(follow_redirects=True)
        req = client.build_request("GET", url, headers=headers)
        r = await client.send(req, stream=True)
        
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail="Không thể tải video từ máy chủ TikTok.")
            
        return StreamingResponse(
            r.aiter_bytes(),
            media_type=r.headers.get("content-type", "video/mp4"),
            headers={"Content-Disposition": "attachment; filename=tiktok_video.mp4"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
