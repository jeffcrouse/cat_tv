"""YouTube integration for fetching video URLs."""

import logging
import random
from typing import Optional, List, Dict, Any
import yt_dlp
import requests

from .config import config

logger = logging.getLogger(__name__)

class YouTubeManager:
    """Manages YouTube video fetching and URL extraction."""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',
            'nocheckcertificate': True,
        }
        # Cache successful videos to avoid re-searching
        self._video_cache = []
        self._cache_timestamp = 0
        import time
        self.time = time
        
    def get_cached_videos(self) -> List[Dict[str, Any]]:
        """Get cached cat TV videos if available and recent."""
        # Cache videos for 1 hour
        cache_lifetime = 3600
        current_time = self.time.time()
        
        if (self._video_cache and 
            current_time - self._cache_timestamp < cache_lifetime):
            logger.info(f"Using cached videos ({len(self._video_cache)} available)")
            return self._video_cache.copy()
        
        return []
    
    def search_videos_fast(self, query: str = "cat tv", max_results: int = 10) -> List[Dict[str, Any]]:
        """Fast search with caching and optimized settings."""
        # Try cache first
        cached = self.get_cached_videos()
        if cached:
            return cached
        
        logger.info(f"Searching YouTube for: {query}")
        try:
            # Use faster settings
            fast_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Much faster - only gets basic info
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(fast_opts) as ydl:
                search_query = f"ytsearch{max_results}:{query}"
                result = ydl.extract_info(search_query, download=False)
                
                videos = []
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry and entry.get('id'):
                            videos.append({
                                'id': entry.get('id'),
                                'title': entry.get('title', 'Unknown'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'duration': entry.get('duration'),
                                'channel': entry.get('uploader', 'Unknown'),
                                'is_live': entry.get('is_live', False),
                            })
                
                # Cache the results
                if videos:
                    self._video_cache = videos
                    self._cache_timestamp = self.time.time()
                
                logger.info(f"Found {len(videos)} videos for query: {query}")
                return videos
                
        except Exception as e:
            logger.error(f"Fast search failed: {e}")
            return []
    
    def search_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for YouTube videos by query."""
        try:
            search_opts = {
                **self.ydl_opts,
                'default_search': 'ytsearch',
                'max_downloads': max_results,
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                search_query = f"ytsearch{max_results}:{query}"
                result = ydl.extract_info(search_query, download=False)
                
                videos = []
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry:
                            videos.append({
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'url': entry.get('webpage_url'),
                                'duration': entry.get('duration'),
                                'channel': entry.get('channel'),
                                'is_live': entry.get('is_live', False),
                            })
                
                logger.info(f"Found {len(videos)} videos for query: {query}")
                return videos
                
        except Exception as e:
            logger.error(f"Failed to search videos: {e}")
            return []
    
    def get_channel_videos(self, channel_url: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get recent videos from a YouTube channel."""
        try:
            opts = {
                **self.ydl_opts,
                'playlistend': max_results,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(channel_url, download=False)
                
                videos = []
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry:
                            videos.append({
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'duration': entry.get('duration'),
                            })
                
                logger.info(f"Found {len(videos)} videos from channel: {channel_url}")
                return videos
                
        except Exception as e:
            logger.error(f"Failed to get channel videos: {e}")
            return []
    
    def get_stream_url(self, video_url: str) -> Optional[str]:
        """Extract the actual stream URL from a YouTube video."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Get the best format URL
                if 'url' in info:
                    return info['url']
                elif 'formats' in info:
                    # Find best format with both video and audio
                    for fmt in reversed(info['formats']):
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                            return fmt['url']
                    # Fallback to any format with URL
                    for fmt in info['formats']:
                        if 'url' in fmt:
                            return fmt['url']
                            
                logger.warning(f"No stream URL found for: {video_url}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None
    
    def get_random_cat_video(self) -> Optional[Dict[str, Any]]:
        """Get a random cat video for entertainment."""
        queries = [
            "cat tv for cats to watch birds",
            "videos for cats to watch mice",
            "cat entertainment video birds squirrels",
            "8 hour bird video for cats",
            "cat tv mice",
            "garden birds for cats to watch",
        ]
        
        query = random.choice(queries)
        videos = self.search_videos(query, max_results=10)
        
        if videos:
            # Prefer longer videos (likely to be compilations)
            # Handle None durations (live streams)
            videos.sort(key=lambda x: x.get('duration') or 0, reverse=True)
            
            # Filter for live streams or long videos
            long_videos = [v for v in videos if (v.get('duration') or 0) > 1800 or v.get('is_live')]
            
            if long_videos:
                return random.choice(long_videos[:3])
            else:
                return videos[0] if videos else None
        
        return None
    
    def search_with_api(self, query: str) -> Optional[Dict[str, Any]]:
        """Search using YouTube API if available."""
        if not config.YOUTUBE_API_KEY:
            return None
            
        try:
            url = "https://youtube.googleapis.com/youtube/v3/search"
            params = {
                'key': config.YOUTUBE_API_KEY,
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': 5,
                'videoDuration': 'long',  # Prefer longer videos
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get('items'):
                videos = []
                for item in data['items']:
                    videos.append({
                        'id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                        'channel': item['snippet']['channelTitle'],
                    })
                
                return random.choice(videos) if videos else None
                
        except Exception as e:
            logger.error(f"YouTube API search failed: {e}")
            
        return None