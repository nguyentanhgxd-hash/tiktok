import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = yt_dlp.YoutubeDL({'quiet': True}).extract_info(url, download=False)
            
            title = info.get('title', 'Video TikTok')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration_string', 'N/A')
            
            formats_list = []
            formats = info.get('formats', [info])
            
            for f in formats:
                if f.get('url'):
                    formats_list.append({
                        'quality': f.get('format_note') or f.get('resolution') or 'HD',
                        'ext': f.get('ext', 'mp4'),
                        'vcodec': f.get('vcodec', 'none'),
                        'acodec': f.get('acodec', 'none'),
                        'url': f.get('url')
                    })
            
            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "formats": formats_list
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/proxy-download")
async def proxy_download(url: str, filename: str = "tiktok_video.mp4"):
    # Sử dụng headers giả lập hoàn chỉnh để đánh lừa bộ lọc Akamai của TikTok
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Range": "bytes=0-"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            r = await client.get(url, headers=headers)
            
            # Nếu TikTok trả về lỗi 403 hoặc 400 ở proxy, ta cho phép redirect hoặc thử lại bằng cách nới lỏng headers
            if r.status_code not in [200, 206]:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                
            if r.status_code not in [200, 206]:
                raise HTTPException(status_code=400, detail="Không thể tải file từ máy chủ TikTok.")
                
            media_type = "audio/mpeg" if ".mp3" in filename.lower() else "video/mp4"

            return StreamingResponse(
                r.aiter_bytes(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Accept-Ranges": "bytes"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
