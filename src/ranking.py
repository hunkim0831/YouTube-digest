"""
ranking.py
─────────────────────────────────────────────────────
YouTube Data API로 영상 조회수 가져와서
'시간당 평균 조회수' 기준 상위 N편 선정.

점수 공식:
    score = view_count / max(hours_since_upload, 1.0)

이유:
- 단순 조회수는 오래된 영상에 유리 → 불공정
- 시간으로 나누면 momentum(화제성)이 정확히 반영
- max(_, 1.0)으로 너무 새 영상의 noise 안정화
"""

import os
from datetime import datetime, timezone
from googleapiclient.discovery import build


def fetch_video_metadata(video_ids: list[str], api_key: str) -> dict:
    """
    YouTube Data API로 여러 영상의 메타데이터를 한 번에 조회.
    
    Returns: {video_id: {view_count, published_at}, ...}
    """
    if not video_ids:
        return {}
    
    youtube = build("youtube", "v3", developerKey=api_key)
    
    # 한 번에 최대 50개까지 조회 가능 (본인 케이스는 보통 15개 미만)
    result = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            response = youtube.videos().list(
                part="statistics,snippet",
                id=",".join(batch),
            ).execute()
            
            for item in response.get("items", []):
                vid = item["id"]
                stats = item.get("statistics", {})
                snippet = item.get("snippet", {})
                
                result[vid] = {
                    "view_count": int(stats.get("viewCount", 0)),
                    "published_at": snippet.get("publishedAt", ""),
                }
        except Exception as e:
            print(f"[ranking] ❌ YouTube API 호출 실패: {type(e).__name__}: {e}")
    
    return result


def rank_by_velocity(videos: list[dict], top_n: int = 5) -> list[dict]:
    """
    시간당 평균 조회수(velocity) 기준으로 상위 N편 선정.
    
    Args:
        videos: [{title, video_id, url, published, ...}, ...]
        top_n: 선정할 영상 수
    
    Returns: 점수 추가된 상위 N편의 영상 리스트
    """
    if not videos:
        return []
    
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[ranking] ⚠️  YOUTUBE_API_KEY 없음, 시간순으로 반환")
        return videos[:top_n]
    
    print(f"[ranking] {len(videos)}편 중 상위 {top_n}편 선정 (시간당 조회수 기준)")
    
    # 메타데이터 조회
    video_ids = [v["video_id"] for v in videos]
    metadata = fetch_video_metadata(video_ids, api_key)
    
    # 각 영상에 score 부여
    now = datetime.now(timezone.utc)
    scored = []
    for v in videos:
        vid = v["video_id"]
        meta = metadata.get(vid)
        
        if not meta:
            print(f"[ranking]   '{v['title'][:40]}...' 메타데이터 없음, skip")
            continue
        
        # 업로드 시각 파싱
        try:
            published_dt = datetime.fromisoformat(
                meta["published_at"].replace("Z", "+00:00")
            )
            hours_since = (now - published_dt).total_seconds() / 3600
        except Exception:
            hours_since = 24.0  # 파싱 실패 시 기본값
        
        # 안정화: 최소 1시간으로 보정 (너무 새 영상의 noise 방지)
        effective_hours = max(hours_since, 1.0)
        view_count = meta["view_count"]
        score = view_count / effective_hours
        
        v_with_score = dict(v)
        v_with_score["view_count"] = view_count
        v_with_score["hours_since_upload"] = round(hours_since, 1)
        v_with_score["velocity_score"] = round(score, 1)
        scored.append(v_with_score)
    
    # 점수 기준 정렬 → 상위 N편
    scored.sort(key=lambda v: v["velocity_score"], reverse=True)
    top_videos = scored[:top_n]
    
    # 로그 출력
    print(f"[ranking] 선정된 영상:")
    for i, v in enumerate(top_videos, 1):
        print(f"  {i}. [{v['velocity_score']:.0f} views/h] {v['title'][:50]}")
        print(f"     조회수 {v['view_count']:,} / {v['hours_since_upload']}h 경과")
    
    return top_videos


if __name__ == "__main__":
    # 단독 실행 시 테스트
    test_videos = [
        {
            "title": "테스트 영상",
            "video_id": "dQw4w9WgXcQ",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "published": "2009-10-25T06:57:33Z",
            "channel_name": "Test",
        },
    ]
    result = rank_by_velocity(test_videos, top_n=1)
    print(f"\n결과: {result}")
