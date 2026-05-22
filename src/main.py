"""
main.py
─────────────────────────────────────────────────────
YouTube Digest 전체 파이프라인 진입점.

흐름:
  1. channels.yaml 로드
  2. 각 채널의 최근 영상 RSS 수집 (후보 풀)
  3. YouTube Data API로 조회수 가져와 상위 N편 선정 (ranking)
  4. 선정된 영상별로 자막 추출 → 요약 생성
  5. 결과를 Gmail로 발송
"""

import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fetch_videos import fetch_recent_videos
from ranking import rank_by_velocity
from transcript import get_transcript
from summarize import summarize_video
from send_email import send_digest_email


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "channels.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"필수 환경변수 누락: {name}")
    return value


def main():
    print("=" * 60)
    print("YouTube Digest 시작")
    print("=" * 60)
    
    gemini_api_key = get_env("GEMINI_API_KEY")
    gmail_address = get_env("GMAIL_ADDRESS")
    gmail_password = get_env("GMAIL_APP_PASSWORD")
    
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
    
    # 1단계: 채널별 신규 영상 수집 (후보 풀)
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
    
    print(f"\n총 후보: {len(all_videos)}편")
    
    # 2단계: 시간당 조회수 기준 상위 max_videos편 선정
    top_videos = rank_by_velocity(all_videos, top_n=max_videos)
    print(f"\n선정 완료: {len(top_videos)}편 본격 처리\n")
    
    # 3단계: 영상별 자막 추출 → 요약
    summaries = []
    for i, v in enumerate(top_videos, 1):
        print(f"\n─── [{i}/{len(top_videos)}] {v['title'][:50]} ───")
        
        transcript, source = get_transcript(
            video_id=v["video_id"],
            language=v.get("language", "ko"),
            max_chars=max_chars,
        )
        
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
            "view_count": v.get("view_count", 0),
            "velocity_score": v.get("velocity_score", 0),
        })
    
    # 4단계: 메일 발송
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
