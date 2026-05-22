"""
main.py
─────────────────────────────────────────────────────
YouTube Digest 전체 파이프라인 진입점.

흐름:
  1. channels.yaml 로드
  2. 각 채널의 최근 영상 RSS 수집
  3. 영상별로 자막 추출 → 요약 생성
  4. 결과를 Gmail로 발송
"""

import os
import sys
import yaml
from pathlib import Path

# src/ 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from fetch_videos import fetch_recent_videos
from transcript import get_transcript
from summarize import summarize_video
from send_email import send_digest_email


def load_config() -> dict:
    """channels.yaml 로드 (루트 디렉토리에 있다고 가정)."""
    config_path = Path(__file__).parent.parent / "channels.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_env(name: str) -> str:
    """환경변수 필수 로드."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"필수 환경변수 누락: {name}")
    return value


def main():
    print("=" * 60)
    print("YouTube Digest 시작")
    print("=" * 60)
    
    # 환경변수 로드
    gemini_api_key = get_env("GEMINI_API_KEY")
    gmail_address = get_env("GMAIL_ADDRESS")
    gmail_password = get_env("GMAIL_APP_PASSWORD")
    
    # 설정 로드
    config = load_config()
    channels = config["channels"]
    settings = config.get("settings", {})
    lookback_hours = settings.get("lookback_hours", 24)
    max_videos = settings.get("max_videos_per_run", 5)
    max_chars = settings.get("max_transcript_chars", 30000)
    
    print(f"\n[설정]")
    print(f"  채널 수: {len(channels)}")
    print(f"  조회 범위: 최근 {lookback_hours}시간")
    print(f"  최대 처리: {max_videos}편/회\n")
    
    # 1단계: 채널별 신규 영상 수집
    all_videos = []
    for ch in channels:
        videos = fetch_recent_videos(
            channel_id=ch["channel_id"],
            channel_name=ch["name"],
            lookback_hours=lookback_hours,
        )
        for v in videos:
            v["language"] = ch.get("language", "ko")
        all_videos.extend(videos)
    
    if not all_videos:
        print("\n신규 영상 없음. 빈 다이제스트 발송.")
        send_digest_email(
            summaries=[],
            gmail_address=gmail_address,
            gmail_app_password=gmail_password,
        )
        return
    
    # 처리 개수 제한
    all_videos = all_videos[:max_videos]
    print(f"\n총 {len(all_videos)}편 처리 예정\n")
    
    # 2단계: 영상별 자막 추출 → 요약
    summaries = []
    for i, v in enumerate(all_videos, 1):
        print(f"\n─── [{i}/{len(all_videos)}] {v['title'][:50]} ───")
        
        # 자막 추출
        transcript, source = get_transcript(
            video_id=v["video_id"],
            language=v.get("language", "ko"),
            max_chars=max_chars,
        )
        
        # 요약 생성
        summary_text = summarize_video(
            title=v["title"],
            channel=v["channel_name"],
            transcript=transcript,
            api_key=gemini_api_key,
        )
        
        summaries.append({
            "title": v["title"],
            "channel_name": v["channel_name"],
            "url": v["url"],
            "summary": summary_text,
            "transcript_source": source,
        })
    
    # 3단계: 메일 발송
    print(f"\n{'=' * 60}")
    print(f"메일 발송 중... ({len(summaries)}편)")
    print(f"{'=' * 60}")
    send_digest_email(
        summaries=summaries,
        gmail_address=gmail_address,
        gmail_app_password=gmail_password,
    )
    
    print("\n✅ 완료")


if __name__ == "__main__":
    main()
