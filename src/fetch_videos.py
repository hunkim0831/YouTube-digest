"""
fetch_videos.py
─────────────────────────────────────────────────────
유튜브 채널의 RSS 피드를 읽어 최근 N시간 이내의 신규 영상을 반환.
"""

from datetime import datetime, timedelta, timezone
import feedparser


def fetch_recent_videos(channel_id: str, channel_name: str, lookback_hours: int = 24):
    """
    특정 채널에서 최근 N시간 이내의 영상 리스트 반환.
    
    Returns: [{title, video_id, url, published, channel_name}, ...]
    """
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"[fetch_videos] '{channel_name}' RSS 피드 확인 중...")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        print(f"[fetch_videos] ⚠️  RSS 파싱 경고: {feed.bozo_exception}")
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    recent_videos = []
    
    for entry in feed.entries:
        # 'yt:videoId' 필드에서 video_id 추출
        video_id = entry.get("yt_videoid")
        if not video_id:
            continue
        
        # 발행 시각 파싱
        published_str = entry.get("published")
        if not published_str:
            continue
        try:
            published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            continue
        
        # 최근 N시간 이내인지 확인
        if published_dt < cutoff_time:
            continue
        
        recent_videos.append({
            "title": entry.title,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "published": published_dt.isoformat(),
            "channel_name": channel_name,
        })
    
    print(f"[fetch_videos] '{channel_name}' 신규 영상 {len(recent_videos)}편 발견")
    return recent_videos


if __name__ == "__main__":
    # 단독 실행 시 테스트
    videos = fetch_recent_videos(
        channel_id="UChlv4GSd7OQl3js-jkLOnFA",
        channel_name="삼프로TV",
        lookback_hours=24,
    )
    for v in videos:
        print(f"  - [{v['published'][:16]}] {v['title']}")
