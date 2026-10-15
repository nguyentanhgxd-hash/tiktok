import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
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
    # Cấu hình yt-dlp tối ưu tương thích ngược với các bản mới nhất
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
            
            # Xử lý dạng ảnh / slideshow
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
            
            # Nếu không tìm thấy format nào, lấy trực tiếp url gốc của info
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
        # Bắt lỗi chi tiết trả về client để dễ kiểm tra
        raise HTTPException(status_code=400, detail=f"Lỗi bóc tách: {str(e)}")

@app.get("/api/proxy-download")
async def proxy_download(url: str, filename: str = "tiktok_media.mp4"):
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu URL tải xuống.")
    # Sử dụng RedirectResponse chuẩn 303 để trình duyệt tự tải trực tiếp
    return RedirectResponse(url=url, status_code=303)
