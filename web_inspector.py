"""
================================================================================
FocusTracker Pro — Web Inspector Bot / Rail Guard (web_inspector.py)
================================================================================
Role:
  Safeguards against misleading browser tab titles (e.g., a window titled
  "Research Project" that is actually streaming YouTube or playing games).
  
  Workflow:
    1. Checks if the active process is a recognized browser (Chrome, Edge, etc.).
    2. Uses Windows UIAutomation to locate and extract the browser address bar URL.
    3. Asynchronously fetches up to 35KB of HTML and parses the first 70 words
       of meaningful body text (stripping scripts, styling, headers, and footers).
    4. Caches URL snippets for 5 minutes (TTL) to ensure near-zero network & CPU impact.
    5. Feeds the extracted text snippet to `classifier.py` for Rail Guard evaluation.

Linkages:
  - Instantiated by `TrackingEngine` in `tracker.py` as `self.inspector`.
  - Asynchronously calls back into `tracker.py._on_web_inspection_complete()`
    upon completing page inspection.
================================================================================
"""

import re
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Tuple, Callable
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# Section 1: Windows UIAutomation Accessibility API Import
# -----------------------------------------------------------------------------
# uiautomation walks the Windows UI Accessibility tree to read the address bar
try:
    import uiautomation as auto
except ImportError:
    auto = None

# -----------------------------------------------------------------------------
# Section 2: Browser Process Whitelist
# -----------------------------------------------------------------------------
# Set of known web browser process executable names monitored for URL inspection
BROWSER_PROCESSES = {
    'chrome.exe', 'msedge.exe', 'brave.exe', 'firefox.exe',
    'opera.exe', 'opera_gx.exe', 'vivaldi.exe', 'arc.exe',
    'waterfox.exe', 'chromium.exe', 'safari.exe'
}

# -----------------------------------------------------------------------------
# Section 3: WebInspectorBot Class
# -----------------------------------------------------------------------------
class WebInspectorBot:
    """
    Asynchronous web page scraper and UIAutomation URL extractor.
    Enforces the '70-Word AI Web Rail Guard'.
    """

    def __init__(self, max_words: int = 70, cache_ttl: int = 300):
        """
        :param max_words: Number of body words to extract (default: 70 words).
        :param cache_ttl: Time-to-live for cached URL content in seconds (default: 300s = 5m).
        """
        self.max_words = max_words
        self.cache_ttl = cache_ttl
        # In-memory LRU-like cache: key (app:title) -> (timestamp, inspection_dict)
        self._cache: Dict[str, Tuple[float, dict]] = {}
        # Dedicated thread pool for non-blocking HTTP network calls
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="WebInspector")
        self._active_future = None

    def is_browser(self, app_name: str) -> bool:
        """
        Checks whether the specified application binary is a known browser.
        """
        if not app_name:
            return False
        return app_name.lower().strip() in BROWSER_PROCESSES

    # -------------------------------------------------------------------------
    # In-Memory Cache Management
    # -------------------------------------------------------------------------
    def get_cached(self, key: str) -> Optional[dict]:
        """
        Retrieves cached inspection result if it exists and has not expired.
        """
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self.cache_ttl:
                return data
            else:
                del self._cache[key]
        return None

    def set_cache(self, key: str, data: dict):
        """
        Stores an inspection result in memory, pruning oldest entries if cache exceeds 200 items.
        """
        if len(self._cache) > 200:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        self._cache[key] = (time.time(), data)

    # -------------------------------------------------------------------------
    # Windows UIAutomation Browser URL Extraction
    # -------------------------------------------------------------------------
    def extract_browser_url(self, hwnd: int) -> Optional[str]:
        """
        Inspects the accessibility tree of the browser window handle (HWND)
        to extract the active URL text from the address / omnibox input control.
        """
        if not auto or not hwnd or hwnd <= 0:
            return None
        
        try:
            ctrl = auto.ControlFromHandle(hwnd)
            if not ctrl:
                return None

            # Strategy 1: Look for direct EditControl within top 5 depths (Chromium standard)
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

            # Strategy 2: Search direct children controls for address bar name patterns
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

    # -------------------------------------------------------------------------
    # Lightweight Web Scraping (First 70 Words)
    # -------------------------------------------------------------------------
    def fetch_first_70_words(self, url: str) -> Tuple[str, int]:
        """
        Downloads up to 35KB of HTML from the URL with a strict 1.5s timeout,
        parses readable text via BeautifulSoup, and extracts the first ~70 words.
        
        Returns:
            Tuple of (snippet_text, word_count)
        """
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

            # Read max 35KB with a 1.5-second socket timeout to prevent lagging the system
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                raw_bytes = resp.read(35000)
                charset = resp.headers.get_content_charset() or 'utf-8'
                html = raw_bytes.decode(charset, errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')

            # Strip non-text and structural boilerplate elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'aside']):
                tag.decompose()

            # Clean and tokenize body text
            text = ' '.join(soup.get_text().split())
            tokens = text.split()
            words = tokens[:self.max_words]
            snippet = ' '.join(words)

            return snippet, len(words)
        except Exception:
            # Silently fallback on network error or offline / protected intranet sites
            return "", 0

    # -------------------------------------------------------------------------
    # Synchronous Window Inspection Orchestration
    # -------------------------------------------------------------------------
    def inspect(self, hwnd: int, app_name: str, window_title: str) -> dict:
        """
        Executes synchronous inspection of the target window.
        Uses in-memory cache if available; otherwise performs UIAutomation + scrape.
        """
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

        # Fallback if no web snippet was fetched: use window title words as baseline
        if not snippet and window_title:
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

    # -------------------------------------------------------------------------
    # Asynchronous Non-Blocking Inspection
    # -------------------------------------------------------------------------
    def inspect_async(self, hwnd: int, app_name: str, window_title: str, callback: Callable[[dict], None]):
        """
        Submits the inspection job to a background worker thread.
        Once inspection completes, triggers the provided callback with results.
        """
        cache_key = f"{app_name}:{window_title}"
        cached = self.get_cached(cache_key)
        if cached:
            callback(cached)
            return

        def _worker():
            try:
                # Windows UIAutomation requires COM initialization in threaded contexts
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
