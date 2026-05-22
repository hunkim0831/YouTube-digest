"""
transcript.py
─────────────────────────────────────────────────────
영상 자막 추출. 3단계 cascade fallback:
  ① youtube-transcript-api (Webshare proxy 사용)
  ② yt-dlp 자동 자막
  ③ 영상 설명만 (최후 수단)
"""

import os
import subprocess
import tempfile
import re
from pathlib import Path


def _try_youtube_transcript_api(video_id: str, language: str = "ko") -> str | None:
    """1차 시도: youtube-transcript-api (Webshare proxy 사용)
    
    개선:
    - 사용 가능한 자막 목록을 먼저 조회
    - 어떤 언어든 발견되면 그것을 사용
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import WebshareProxyConfig
        
        webshare_username = os.environ.get("WEBSHARE_USERNAME")
        webshare_password = os.environ.get("WEBSHARE_PASSWORD")
        
        if webshare_username and webshare_password:
            print(f"[transcript] Webshare proxy 사용 시도")
            ytt = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=webshare_username,
                    proxy_password=webshare_password,
                )
            )
        else:
            print(f"[transcript] proxy 인증 정보 없음, 직접 시도")
            ytt = YouTubeTranscriptApi()
        
        # 단계적 시도
        language_attempts = [
            [language],
            [language, "en"],
            ["ko", "en"],
        ]
        
        transcript = None
        for langs in language_attempts:
            try:
                transcript = ytt.fetch(video_id, languages=langs)
                if transcript:
                    print(f"[transcript] 언어 {langs}로 자막 발견")
                    break
            except Exception:
                continue
        
        # 마지막 fallback: 사용 가능한 어떤 자막이든
        if not transcript:
            try:
                transcript_list = ytt.list(video_id)
                for t in transcript_list:
                    try:
                        fetched = t.fetch()
                        if fetched:
                            transcript = fetched
                            print(f"[transcript] '{t.language_code}' 자막 발견 (fallback)")
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        
        if not transcript:
            print(f"[transcript] ❌ 사용 가능한 자막 없음")
            return None
        
        text = " ".join([snippet.text for snippet in transcript])
        if text.strip():
            print(f"[transcript] ✅ youtube-transcript-api 성공 ({len(text)}자)")
            return text
        return None
    
    except Exception as e:
        error_type = type(e).__name__
        print(f"[transcript] ❌ youtube-transcript-api 실패: {error_type}")
        error_msg = str(e).split('\n')[0]
        print(f"[transcript]    이유: {error_msg[:150]}")
        return None


def _try_ytdlp(video_id: str, language: str = "ko") -> str | None:
    """2차 시도: yt-dlp로 자동 자막 다운로드 후 파싱"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--write-subs",
                "--sub-langs", f"{language},en,ko",
                "--sub-format", "vtt",
                "-o", output_template,
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"[transcript] yt-dlp 종료 코드 {result.returncode}")
            
            vtt_files = list(Path(tmpdir).glob(f"{video_id}*.vtt"))
            if not vtt_files:
                return None
            
            vtt_text = vtt_files[0].read_text(encoding="utf-8")
            text = _parse_vtt(vtt_text)
            if text.strip():
                print(f"[transcript] ✅ yt-dlp 성공 ({len(text)}자)")
                return text
            return None
    except Exception as e:
        print(f"[transcript] ❌ yt-dlp 실패: {type(e).__name__}")
        return None


def _parse_vtt(vtt_content: str) -> str:
    lines = vtt_content.split("\n")
    text_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if line.isdigit():
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            text_lines.append(clean)
            seen.add(clean)
    return " ".join(text_lines)


def get_transcript(video_id: str, language: str = "ko", max_chars: int = 30000) -> tuple[str, str]:
    print(f"[transcript] video_id={video_id} 자막 추출 시도")
    
    text = _try_youtube_transcript_api(video_id, language)
    if text:
        return text[:max_chars], "youtube-transcript-api"
    
    text = _try_ytdlp(video_id, language)
    if text:
        return text[:max_chars], "yt-dlp"
    
    print(f"[transcript] ⚠️  자막을 가져올 수 없음")
    return "", "unavailable"


if __name__ == "__main__":
    import sys
    test_id = sys.argv[1] if len(sys.argv) > 1 else "dQw4w9WgXcQ"
    text, source = get_transcript(test_id)
    print(f"\n출처: {source}")
    print(f"길이: {len(text)}자")
