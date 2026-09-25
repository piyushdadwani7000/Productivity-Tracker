"""
FocusTracker — Web Inspector Bot (Rail Guard)
Reads the first 70 words of any active browser webpage using UIAutomation + fast lightweight scraping.
Classifies content as Intended Task or Distraction to guard against misleading websites.
"""

import re
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Tuple, Callable
from bs4 import BeautifulSoup

# UIAutomation for Windows accessibility tree inspection
try:
    import uiautomation as auto
except ImportError:
    auto = None

BROWSER_PROCESSES = {
    'chrome.exe', 'msedge.exe', 'brave.exe', 'firefox.exe',
    'opera.exe', 'opera_gx.exe', 'vivaldi.exe', 'arc.exe',
    'waterfox.exe', 'chromium.exe', 'safari.exe'
}

class WebInspectorBot:
    def __init__(self, max_words: int = 70, cache_ttl: int = 300):
        self.max_words = max_words
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, dict]] = {} # key -> (timestamp, data)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="WebInspector")
        self._active_future = None

    def is_browser(self, app_name: str) -> bool:
        if not app_name:
            return False
        return app_name.lower().strip() in BROWSER_PROCESSES

    def get_cached(self, key: str) -> Optional[dict]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self.cache_ttl:
                return data
            else:
                del self._cache[key]
        return None

    def set_cache(self, key: str, data: dict):
        # Keep cache bounded
        if len(self._cache) > 200:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        self._cache[key] = (time.time(), data)

    def extract_browser_url(self, hwnd: int) -> Optional[str]:
        """Extracts active address bar URL from browser window using UIAutomation."""
        if not auto or not hwnd or hwnd <= 0:
            return None
        
        try:
            ctrl = auto.ControlFromHandle(hwnd)
            if not ctrl:
                return None

            # 1. Search for address bar EditControl (optimized depth=5)
            edit = ctrl.EditControl(searchDepth=5)
            if edit.Exists(0, 0):
                try:
                    pattern = edit.GetValuePattern()
                    if pattern:
                        val = pattern.Value.strip()
                        if val and ('.' in val or 'localhost' in val or '/' in val):
                            if not val.startswith(('http://', 'https://')):
                                val = 'https://' + val
                            return val
                except Exception:
                    pass

            # 2. Search children controls for address bar
            for child in ctrl.GetChildren():
                if child.ControlType == auto.ControlType.EditControl or 'address' in child.Name.lower():
                    try:
                        val = child.GetValuePattern().Value.strip()
                        if val and '.' in val:
                            if not val.startswith(('http://', 'https://')):
                                val = 'https://' + val
                            return val
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def fetch_first_70_words(self, url: str) -> Tuple[str, int]:
        """Fetches webpage and extracts the first ~70 words of readable text."""
        if not url or not url.startswith(('http://', 'https://')):
            return "", 0

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
            )

            # Read up to 35KB with a 1.5s timeout for maximum speed
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                raw_bytes = resp.read(35000)
                charset = resp.headers.get_content_charset() or 'utf-8'
                html = raw_bytes.decode(charset, errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')

            # Strip non-content elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'aside']):
                tag.decompose()

            text = ' '.join(soup.get_text().split())
            tokens = text.split()
            words = tokens[:self.max_words]
            snippet = ' '.join(words)

            return snippet, len(words)
        except Exception as e:
            # Fallback for localhost or connection errors
            return "", 0

    def inspect(self, hwnd: int, app_name: str, window_title: str) -> dict:
        """Synchronously inspects a window and extracts the 70-word snippet (uses cache)."""
        cache_key = f"{app_name}:{window_title}"
        cached = self.get_cached(cache_key)
        if cached:
            return cached

        is_browser = self.is_browser(app_name)
        url = None
        snippet = ""
        word_count = 0

        if is_browser:
            url = self.extract_browser_url(hwnd)
            if url:
                snippet, word_count = self.fetch_first_70_words(url)

        # Fallback if no web snippet was fetched
        if not snippet and window_title:
            # Use window title words as fallback snippet
            words = window_title.split()[:self.max_words]
            snippet = ' '.join(words)
            word_count = len(words)

        result = {
            'is_browser': is_browser,
            'url': url or '',
            'snippet': snippet,
            'word_count': word_count,
            'timestamp': time.time()
        }

        self.set_cache(cache_key, result)
        return result

    def inspect_async(self, hwnd: int, app_name: str, window_title: str, callback: Callable[[dict], None]):
        """Asynchronously executes the inspection in a background worker thread."""
        cache_key = f"{app_name}:{window_title}"
        cached = self.get_cached(cache_key)
        if cached:
            callback(cached)
            return

        def _worker():
            try:
                if auto:
                    with auto.UIAutomationInitializerInThread(True):
                        res = self.inspect(hwnd, app_name, window_title)
                else:
                    res = self.inspect(hwnd, app_name, window_title)
            except Exception:
                res = self.inspect(hwnd, app_name, window_title)
                
            if callback:
                callback(res)

        self._executor.submit(_worker)
