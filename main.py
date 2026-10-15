import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
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
    if not url:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp đường dẫn TikTok!")
        
    # 1. ƯU TIÊN LẤY LINK CHẤT LƯỢNG CAO TỪ API DỰ PHÒNG
    try:
        with httpx.Client(timeout=8.0) as client:
            api_res = client.get(f"https://tikwm.com/api/?url={url}&hd=1")
            if api_res.status_code == 200:
                r_data = api_res.json()
                if r_data.get("code") == 0:
                    data_info = r_data.get("data", {})
                    # Ưu tiên lấy link HD không logo (hdplay), nếu không có thì lấy play
                    video_url = data_info.get("hdplay") or data_info.get("play")
                    music_url = data_info.get("music")
                    cover_url = data_info.get("cover")
                    images = data_info.get("images", [])
                    
                    formats_fallback = []
                    if video_url:
                        formats_fallback.append({'quality': 'Full HD / 4K (Không logo)', 'ext': 'mp4', 'type': 'video', 'url': video_url})
                        formats_fallback.append({'quality': 'SD (Có logo)', 'ext': 'mp4', 'type': 'video', 'url': data_info.get("wmplay", video_url)})
                    if music_url:
                        formats_fallback.append({'quality': 'Audio gốc (MP3)', 'ext': 'mp3', 'type': 'audio', 'url': music_url})
                        
                    if images:
                        for img in images:
                            formats_fallback.append({'quality': 'Ảnh gốc', 'ext': 'jpg', 'type': 'image', 'url': img})
                    elif cover_url:
                        formats_fallback.append({'quality': 'Ảnh gốc', 'ext': 'jpg', 'type': 'image', 'url': cover_url})
                        
                    if formats_fallback:
                        return {
                            "title": data_info.get("title", "Video TikTok Chất Lượng Cao"),
                            "thumbnail": cover_url or "",
                            "duration": str(data_info.get("duration", "N/A")),
                            "formats": formats_fallback
                        }
    except Exception:
        pass

    # 2. PHƯƠNG ÁN DỰ PHÒNG: DÙNG YT-DLP ÉP LẤY LUỒNG VIDEO & ÂM THANH NÉT NHẤT
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # Ép chọn định dạng tốt nhất (kết hợp video nét nhất + audio chuẩn nhất)
        'format': 'bestvideo+bestaudio/best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video TikTok Chất Lượng Cao')
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
                        qual = 'Audio gốc (Chất lượng cao)'
                    else:
                        ftype = 'video'
                        height = f.get('height', 1080)
                        qual = f'Full HD / {height}p (Không logo)' if height >= 720 else f'HD ({height}p)'

                    formats_list.append({
                        'quality': qual,
                        'ext': ext,
                        'type': ftype,
                        'url': f.get('url')
                    })
            
            if formats_list:
                return {
                    "title": title,
                    "thumbnail": thumbnail,
                    "duration": duration,
                    "formats": formats_list
                }
    except Exception:
        pass

    raise HTTPException(status_code=400, detail="Không thể bóc tách link này. Vui lòng kiểm tra lại đường dẫn TikTok!")

@app.get("/api/proxy-download")
async def proxy_download(url: str, filename: str = "tiktok_media.mp4"):
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu URL tải xuống.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code not in [200, 206]:
                raise HTTPException(status_code=400, detail="Không thể tải file từ máy chủ TikTok.")
            
            content_bytes = r.content
            
        media_type = "video/mp4"
        if ".mp3" in filename.lower():
            media_type = "audio/mpeg"
        elif ".jpg" in filename.lower() or ".png" in filename.lower():
            media_type = "image/jpeg"

        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content_bytes)),
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
