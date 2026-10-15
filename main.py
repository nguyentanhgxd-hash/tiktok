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
        'extractor_args': {
            'tiktok': {
                'webpage_download': True
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
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
            
            if not formats_list and info.get('url'):
                formats_list.append({
                    'quality': 'HD',
                    'ext': 'mp4',
                    'type': 'video',
                    'url': info.get('url')
                })
            
            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "formats": formats_list
            }
    except Exception as e:
        # Gọi API dự phòng từ tikwm để lấy link sạch không bị chặn IP datacenter
        try:
            with httpx.Client(timeout=10.0) as client:
                api_res = client.get(f"https://tikwm.com/api/?url={url}")
                if api_res.status_code == 200:
                    r_data = api_res.json()
                    if r_data.get("code") == 0:
                        data_info = r_data.get("data", {})
                        video_url = data_info.get("play")
                        music_url = data_info.get("music")
                        cover_url = data_info.get("cover")
                        
                        formats_fallback = []
                        if video_url:
                            formats_fallback.append({'quality': 'HD', 'ext': 'mp4', 'type': 'video', 'url': video_url})
                        if music_url:
                            formats_fallback.append({'quality': 'Audio', 'ext': 'mp3', 'type': 'audio', 'url': music_url})
                        if cover_url:
                            formats_fallback.append({'quality': 'Ảnh gốc', 'ext': 'jpg', 'type': 'image', 'url': cover_url})
                            
                        return {
                            "title": data_info.get("title", "Video TikTok"),
                            "thumbnail": cover_url or thumbnail,
                            "duration": "N/A",
                            "formats": formats_fallback
                        }
        except Exception:
            pass
            
        raise HTTPException(status_code=400, detail="Không thể bóc tách link này. Vui lòng kiểm tra lại đường dẫn!")

@app.get("/api/proxy-download")
async def proxy_download(url: str, filename: str = "tiktok_media.mp4"):
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu URL tải xuống.")
    
    # Server Render sẽ tải ngầm file từ TikTok về trước, sau đó stream ngược lại cho người dùng
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept": "*/*",
        "Range": "bytes=0-"
    }
    
    try:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
        req = client.build_request("GET", url, headers=headers)
        r = await client.send(req, stream=True)
        
        if r.status_code not in [200, 206]:
            # Thử lại với client không giới hạn khắt khe nếu lần đầu lỗi
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as fallback_client:
                r = await fallback_client.get(url)
                
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
