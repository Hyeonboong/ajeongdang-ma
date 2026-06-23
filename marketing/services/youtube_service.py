import os
import re
from statistics import median
from urllib.parse import parse_qs, urlparse

import requests


YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = 10
SHORTS_MAX_DURATION_SECONDS = 180
MAX_UPLOAD_PAGES = 5

MOCK_VIDEO_METRICS = {
    "video_id": "mock-video-id",
    "channel_id": "mock-channel-id",
    "channel_name": "집대성 예시 채널",
    "subscriber_count": 1200000,
    "uploads_playlist_id": "mock-uploads-playlist-id",
    "video_title": "인터넷 가입 혜택 비교 광고 영상",
    "view_count": 950000,
    "like_count": 12000,
    "comment_count": 850,
    "published_at": "2026-06-01",
}

MOCK_RECENT_VIDEO_STATS = {
    "recent_video_count": 10,
    "average_view_count": 765000,
    "median_view_count": 745000,
    "min_view_count": 420000,
    "max_view_count": 1200000,
    "view_counts": [1200000, 950000, 880000, 810000, 760000, 730000, 690000, 620000, 590000, 420000],
}

MOCK_CHANNEL_ANALYSIS_METRICS = {
    "channel_id": "mock-channel-id",
    "channel_name": "집대성 예시 채널",
    "subscriber_count": 1200000,
    "total_view_count": 38000000,
    "video_count": 126,
    "uploads_playlist_id": "mock-uploads-playlist-id",
    "recent_video_count": 10,
    "recent_latest_views": 980000,
    "recent_avg_views": 765000,
    "recent_median_views": 745000,
    "recent_min_views": 420000,
    "recent_max_views": 1200000,
    "recent_videos": [
        {
            "video_id": "mock-video-1",
            "title": "인터넷 가입 혜택 비교 광고 영상",
            "view_count": 1200000,
            "like_count": 16000,
            "comment_count": 980,
            "published_at": "2026-06-01",
        },
        {
            "video_id": "mock-video-2",
            "title": "생활비 아끼는 통신 상품 비교",
            "view_count": 950000,
            "like_count": 12000,
            "comment_count": 850,
            "published_at": "2026-05-24",
        },
        {
            "video_id": "mock-video-3",
            "title": "렌탈 서비스 고르는 법",
            "view_count": 880000,
            "like_count": 10500,
            "comment_count": 690,
            "published_at": "2026-05-16",
        },
        {
            "video_id": "mock-video-4",
            "title": "이사 전 꼭 확인할 체크리스트",
            "view_count": 810000,
            "like_count": 9800,
            "comment_count": 610,
            "published_at": "2026-05-09",
        },
        {
            "video_id": "mock-video-5",
            "title": "휴대폰 요금제 비교 상담 후기",
            "view_count": 760000,
            "like_count": 9200,
            "comment_count": 540,
            "published_at": "2026-05-02",
        },
    ],
}


def extract_video_id(url):
    parsed_url = urlparse(url)
    host = parsed_url.netloc.lower()

    if host in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        if parsed_url.path == "/watch":
            return parse_qs(parsed_url.query).get("v", [""])[0]
        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/shorts/", 1)[1].split("/")[0]

    if host == "youtu.be":
        return parsed_url.path.strip("/").split("/")[0]

    return ""


def extract_channel_identifier(url):
    parsed_url = urlparse(url)
    host = parsed_url.netloc.lower()
    path = parsed_url.path.strip("/")

    if host not in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        return {"type": "", "value": ""}

    if path.startswith("@"):
        return {"type": "handle", "value": path.split("/", 1)[0].lstrip("@")}

    if path.startswith("channel/"):
        return {"type": "channel_id", "value": path.split("channel/", 1)[1].split("/")[0]}

    return {"type": "", "value": ""}


def get_video_metrics(url):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        metrics = MOCK_VIDEO_METRICS.copy()
        metrics["video_id"] = extract_video_id(url) or metrics["video_id"]
        return metrics

    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("유효한 유튜브 영상 ID를 찾을 수 없습니다.")

    video_data = _youtube_get(
        "videos",
        {
            "part": "snippet,statistics",
            "id": video_id,
            "key": api_key,
        },
    )
    video_items = video_data.get("items", [])
    if not video_items:
        raise ValueError("YouTube API에서 영상 정보를 찾을 수 없습니다.")

    video_item = video_items[0]
    snippet = video_item.get("snippet", {})
    statistics = video_item.get("statistics", {})
    channel_id = snippet.get("channelId", "")

    channel_data = _youtube_get(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id,
            "key": api_key,
        },
    )
    channel_items = channel_data.get("items", [])
    if not channel_items:
        raise ValueError("YouTube API에서 채널 정보를 찾을 수 없습니다.")

    channel_item = channel_items[0]
    channel_statistics = channel_item.get("statistics", {})
    related_playlists = channel_item.get("contentDetails", {}).get("relatedPlaylists", {})
    hidden_subscriber_count = channel_statistics.get("hiddenSubscriberCount") is True

    return {
        "video_id": video_id,
        "channel_id": channel_id,
        "channel_name": snippet.get("channelTitle", ""),
        "subscriber_count": 0 if hidden_subscriber_count else _int_value(channel_statistics.get("subscriberCount")),
        "uploads_playlist_id": related_playlists.get("uploads", ""),
        "video_title": snippet.get("title", ""),
        "view_count": _int_value(statistics.get("viewCount")),
        "like_count": _int_value(statistics.get("likeCount")),
        "comment_count": _int_value(statistics.get("commentCount")),
        "published_at": (snippet.get("publishedAt") or "")[:10],
    }


def get_channel_recent_video_metrics(url, limit=10):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        metrics = MOCK_VIDEO_METRICS.copy()
        metrics.update(MOCK_RECENT_VIDEO_STATS)
        metrics["video_id"] = extract_video_id(url) or metrics["video_id"]
        return metrics

    video_metrics = get_video_metrics(url)
    uploads_playlist_id = video_metrics.get("uploads_playlist_id")
    if not uploads_playlist_id:
        raise ValueError("채널의 업로드 재생목록 ID를 찾을 수 없습니다.")

    recent_items = _get_recent_long_form_video_items(uploads_playlist_id, api_key, limit)
    if not recent_items:
        raise ValueError("YouTube API에서 최근 일반 영상 통계를 찾을 수 없습니다.")

    view_counts = [_int_value(item.get("statistics", {}).get("viewCount")) for item in recent_items]
    video_metrics.update(
        {
            "recent_video_count": len(view_counts),
            "average_view_count": round(sum(view_counts) / len(view_counts), 2) if view_counts else 0,
            "median_view_count": median(view_counts) if view_counts else 0,
            "min_view_count": min(view_counts) if view_counts else 0,
            "max_view_count": max(view_counts) if view_counts else 0,
            "view_counts": view_counts,
        }
    )
    return video_metrics


def get_mock_channel_analysis_metrics():
    metrics = MOCK_CHANNEL_ANALYSIS_METRICS.copy()
    metrics["recent_videos"] = [video.copy() for video in MOCK_CHANNEL_ANALYSIS_METRICS["recent_videos"]]
    return metrics


def get_channel_analysis_metrics(channel_url, limit=10):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return get_mock_channel_analysis_metrics()

    identifier = extract_channel_identifier(channel_url)
    if not identifier["value"]:
        raise ValueError("지원하는 유튜브 채널 URL이 아닙니다. @handle 또는 /channel/CHANNEL_ID URL을 입력해주세요.")

    channel_params = {
        "part": "snippet,statistics,contentDetails",
        "key": api_key,
    }
    if identifier["type"] == "handle":
        channel_params["forHandle"] = identifier["value"]
    else:
        channel_params["id"] = identifier["value"]

    channel_data = _youtube_get("channels", channel_params)
    channel_items = channel_data.get("items", [])
    if not channel_items:
        raise ValueError("YouTube API에서 채널 정보를 찾을 수 없습니다.")

    channel_item = channel_items[0]
    snippet = channel_item.get("snippet", {})
    statistics = channel_item.get("statistics", {})
    related_playlists = channel_item.get("contentDetails", {}).get("relatedPlaylists", {})
    hidden_subscriber_count = statistics.get("hiddenSubscriberCount") is True
    uploads_playlist_id = related_playlists.get("uploads", "")
    if not uploads_playlist_id:
        raise ValueError("채널의 업로드 재생목록 ID를 찾을 수 없습니다.")

    video_items = _get_recent_long_form_video_items(uploads_playlist_id, api_key, limit)
    if not video_items:
        raise ValueError("YouTube API에서 최근 일반 영상 통계를 찾을 수 없습니다.")

    recent_videos = []
    for item in video_items:
        item_snippet = item.get("snippet", {})
        item_statistics = item.get("statistics", {})
        recent_videos.append(
            {
                "video_id": item.get("id", ""),
                "title": item_snippet.get("title", ""),
                "view_count": _int_value(item_statistics.get("viewCount")),
                "like_count": _int_value(item_statistics.get("likeCount")),
                "comment_count": _int_value(item_statistics.get("commentCount")),
                "published_at": (item_snippet.get("publishedAt") or "")[:10],
            }
        )

    view_counts = [video["view_count"] for video in recent_videos]
    return {
        "channel_id": channel_item.get("id", ""),
        "channel_name": snippet.get("title", ""),
        "subscriber_count": 0 if hidden_subscriber_count else _int_value(statistics.get("subscriberCount")),
        "total_view_count": _int_value(statistics.get("viewCount")),
        "video_count": _int_value(statistics.get("videoCount")),
        "uploads_playlist_id": uploads_playlist_id,
        "recent_video_count": len(recent_videos),
        "recent_latest_views": recent_videos[0]["view_count"] if recent_videos else 0,
        "recent_avg_views": round(sum(view_counts) / len(view_counts), 2) if view_counts else 0,
        "recent_median_views": median(view_counts) if view_counts else 0,
        "recent_min_views": min(view_counts) if view_counts else 0,
        "recent_max_views": max(view_counts) if view_counts else 0,
        "recent_videos": recent_videos,
    }


def _get_recent_long_form_video_items(uploads_playlist_id, api_key, limit):
    long_form_items = []
    page_token = ""

    for _ in range(MAX_UPLOAD_PAGES):
        playlist_params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            playlist_params["pageToken"] = page_token

        playlist_data = _youtube_get("playlistItems", playlist_params)
        playlist_items = playlist_data.get("items", [])
        video_ids = [
            item.get("contentDetails", {}).get("videoId")
            for item in playlist_items
            if item.get("contentDetails", {}).get("videoId")
        ]
        if not video_ids:
            break

        video_data = _youtube_get(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": api_key,
            },
        )
        video_item_map = {item.get("id", ""): item for item in video_data.get("items", [])}

        for video_id in video_ids:
            item = video_item_map.get(video_id)
            if not item:
                continue
            duration = item.get("contentDetails", {}).get("duration", "")
            if _iso8601_duration_seconds(duration) <= SHORTS_MAX_DURATION_SECONDS:
                continue
            long_form_items.append(item)
            if len(long_form_items) >= limit:
                return long_form_items

        page_token = playlist_data.get("nextPageToken", "")
        if not page_token:
            break

    return long_form_items


def _iso8601_duration_seconds(value):
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _youtube_get(resource, params):
    url = f"{YOUTUBE_API_BASE_URL}/{resource}"
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"YouTube API 호출에 실패했습니다: {exc}") from exc

    data = response.json()
    if "error" in data:
        error = data["error"]
        message = error.get("message", "YouTube API 오류가 발생했습니다.")
        raise RuntimeError(message)
    return data


def _int_value(value):
    if value is None or value == "":
        return 0
    return int(value)
