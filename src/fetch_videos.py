"""
fetch_videos.py - YouTube Data API 버전
"""
import os
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build


def fetch_recent_videos(channel_id, channel_name, lookback_hours=24):
    """YouTube Data API로 채널의 최근 영상 가져오기"""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print(f"[fetch_videos] ❌ YOUTUBE_API_KEY 없음")
        return []
    
    print(f"[fetch_videos] '{channel_name}' 영상 목록 조회 (YouTube Data API)")
    
    youtube = build("youtube", "v3", developerKey=api_key)
    
    # 1단계: 채널의 upload playlist ID 가져오기
    try:
        ch_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id,
        ).execute()
        
        if not ch_response.get("items"):
            print(f"[fetch_videos] ❌ 채널을 찾을 수 없음: {channel_id}")
            return []
        
        uploads_playlist_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print(f"[fetch_videos] ❌ 채널 정보 조회 실패: {e}")
        return []
    
    # 2단계: upload playlist에서 최근 영상 가져오기
    try:
        pl_response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=25,  # 충분히 많이 가져와서 시간 필터링
        ).execute()
    except Exception as e:
        print(f"[fetch_videos] ❌ 영상 목록 조회 실패: {e}")
        return []
    
    # 3단계: 시간 필터링
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    recent_videos = []
    
    for item in pl_response.get("items", []):
        snippet = item["snippet"]
        video_id = item["contentDetails"]["videoId"]
        published_str = snippet.get("publishedAt", "")
        
        try:
            published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            continue
        
        if published_dt < cutoff_time:
            continue
        
        recent_videos.append({
            "title": snippet["title"],
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "published": published_dt.isoformat(),
            "channel_name": channel_name,
        })
    
    print(f"[fetch_videos] '{channel_name}' 신규 영상 {len(recent_videos)}편 발견")
    return recent_videos


if __name__ == "__main__":
    videos = fetch_recent_videos(
        channel_id="UChlv4GSd7OQl3js-jkLOnFA",
        channel_name="삼프로TV",
        lookback_hours=24,
    )
    for v in videos:
        print(f"  - [{v['published'][:16]}] {v['title']}")
