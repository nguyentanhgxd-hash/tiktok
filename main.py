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
    # Cấu hình yt-dlp tối ưu để né cơ chế chặn mới của TikTok
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'extractor_args': {
            'tiktok': {
                'webpage_download': True
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.tiktok.com/',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Video TikTok')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration_string', 'N/A')
            
            formats_list = []
            
            # Xử lý trường hợp TikTok dạng ảnh (Slideshow / Image post)
            if 'entries' in info:
                for entry in info['entries']:
                    if 'url' in entry:
                        formats_list.append({
                            'quality': 'Ảnh gốc',
                            'ext': 'jpg',
                            'type': 'image',
                            'url': entry['url']
                        })
            
            formats = info.get('formats', [info])
            for f in formats:
                if f.get('url'):
                    ext = f.get('ext', 'mp4')
                    vcodec = f.get('vcodec', 'none')
                    acodec = f.get('acodec', 'none')
                    
                    if ext in ['jpg', 'png', 'webp']:
                        ftype = 'image'
                    elif vcodec == 'none' and acodec != 'none':
                        ftype = 'audio'
                    else:
                        ftype = 'video'

                    formats_list.append({
                        'quality': f.get('format_note') or f.get('resolution') or 'HD',
                        'ext': ext,
                        'type': ftype,
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
async def proxy_download(url: str, filename: str = "tiktok_media.mp4"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept": "*/*",
        "Range": "bytes=0-"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code not in [200, 206]:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                
            if r.status_code not in [200, 206]:
                raise HTTPException(status_code=400, detail="Không thể tải file từ máy chủ TikTok.")
                
            media_type = "video/mp4"
            if ".mp3" in filename.lower():
                media_type = "audio/mpeg"
            elif ".jpg" in filename.lower() or ".png" in filename.lower():
                media_type = "image/jpeg"

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
