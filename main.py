import urllib.parse
from fastapi import FastAPI, HTTPException
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


def clean_url(url: str) -> str:
    """Làm sạch URL chung cho cả Facebook và TikTok."""
    if not url:
        return url
    return url.strip()


@app.get("/api/download")
def download_media(url: str):
    if not url:
        raise HTTPException(
            status_code=400, detail="Vui lòng cung cấp URL video!"
        )

    target_url = clean_url(url)

    # Cấu hình yt-dlp tối ưu cho cả Facebook và TikTok không dính logo
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)

            if "entries" in info and len(info["entries"]) > 0:
                info = info["entries"][0]

            formats_list = []
            video_url = info.get("url")
            audio_url = None

            # Bóc tách chi tiết các định dạng luồng (nếu có)
            if info.get("formats"):
                for fmt in info["formats"]:
                    fmt_url = fmt.get("url")
                    vcodec = fmt.get("vcodec", "none")
                    acodec = fmt.get("acodec", "none")

                    if not fmt_url:
                        continue

                    # Bắt luồng âm thanh riêng (cho TikTok/Facebook audio)
                    if vcodec == "none" and acodec != "none" and not audio_url:
                        audio_url = fmt_url

            # Đối với TikTok, yt-dlp thường trả thẳng video gốc không dính logo qua info.get('url')
            if video_url:
                formats_list.append(
                    {
                        "quality": "No Watermark (HD/SD)",
                        "desc": "Video gốc không dính logo",
                        "ext": "mp4",
                        "url": video_url,
                    }
                )

            # Thêm tùy chọn Audio / MP3
            final_audio_url = audio_url or video_url
            if final_audio_url:
                formats_list.append(
                    {
                        "quality": "MP3 Audio",
                        "desc": "Tệp âm thanh chuẩn",
                        "ext": "m4a",
                        "url": final_audio_url,
                    }
                )

            # Thêm Ảnh bìa / Thumbnail
            thumbnail_url = info.get("thumbnail")
            if thumbnail_url:
                formats_list.append(
                    {
                        "quality": "IMAGE",
                        "desc": "Ảnh bìa video",
                        "ext": "jpg",
                        "url": thumbnail_url,
                    }
                )

            if not formats_list:
                raise Exception("Không tìm thấy tệp video trực tiếp.")

            return {
                "title": info.get("title") or "TikTok / Facebook Media",
                "thumbnail": thumbnail_url,
                "duration": info.get("duration_string") or "N/A",
                "formats": formats_list,
            }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=(
                "Không thể bóc tách nội dung này. Vui lòng kiểm tra lại đường"
                " link TikTok hoặc Facebook!"
            ),
        )
