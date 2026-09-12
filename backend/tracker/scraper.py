"""
Solution scraper for leetcode.ca.

Two-stage pipeline based on inspected HTML structure:

Stage 1 — https://leetcode.ca/all/{leetcode_id}.html
  Layout: Old Bootstrap site.
  - <h1>N. Title</h1>
  - <div class="markdown-body div-width"> — problem description paragraphs
  - <h3>Problem Solution</h3> immediately followed by <a href="..."> — solution URL

Stage 2 — the dedicated solution blog-post URL discovered in Stage 1
  Layout: Jekyll / UIKit site.
  - <h1 id="question">Question</h1>  → description paragraphs
  - <h1 id="algorithm">Algorithm</h1> → explanation paragraphs
  - <h1 id="code">Code</h1>
  - <ul class="uk-tab"> → language tab names (Java / C++ / Python / Go …)
  - <ul class="uk-switcher"> → one <li> per language containing a
      <div class="language-python highlighter-rouge"><pre class="highlight"><code>…</code></pre></div>
  - Complexity often embedded in C++ comments: "// Time: O(N)"

Returns a structured dict — never proxies raw HTML to clients.
"""
import re
import time
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tracker.utils.problem_formatter import parse_structured_statement

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_text(element) -> str:
    """Return clean text from a BS4 element, normalising whitespace."""
    if element is None:
        return ''
    return element.get_text(separator='\n', strip=True)


def _collect_siblings_until_heading(start_element, stop_tags=('h1', 'h2', 'h3')):
    """
    Walk next siblings from *start_element* collecting text until we hit a
    heading tag listed in *stop_tags* or a section barrier (like solutions/algorithm/code).
    Returns collected plain text.
    """
    parts = []
    curr = start_element.find_next_sibling() if start_element else None
    while curr:
        txt_lower = curr.get_text().strip().lower()
        if curr.name in stop_tags:
            # If curr is an h3/h4 with 'Example' or 'Constraint', it belongs to the statement
            if curr.name in ('h3', 'h4') and any(w in txt_lower for w in ('example', 'constraint', 'note', 'follow')):
                pass
            else:
                break

        # Stop if encountering major post-statement section headings
        if curr.name in ('h1', 'h2', 'h3'):
            if any(w in txt_lower for w in ('solution', 'algorithm', 'code', 'all problem', 'complexity')):
                break

        # Skip UIkit tab/switcher elements (they belong to code, not text)
        classes = curr.get('class') or []
        if 'uk-tab' in classes or 'uk-switcher' in classes:
            break
        t = curr.get_text(separator='\n', strip=True)
        if t:
            parts.append(t)
        curr = curr.find_next_sibling()
    return '\n\n'.join(parts).strip()


# ---------------------------------------------------------------------------
# Main scraper class
# ---------------------------------------------------------------------------

class LeetCodeCaScraper:
    BASE_URL = 'https://leetcode.ca'
    ALL_URL_TEMPLATE = 'https://leetcode.ca/all/{leetcode_id}.html'

    MIN_REQUEST_INTERVAL = 1.2   # seconds between requests (polite scraping)
    REQUEST_TIMEOUT = 20          # seconds

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    _last_request_time: float = 0.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    def _rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        LeetCodeCaScraper._last_request_time = time.monotonic()

    def _fetch_html(self, url: str) -> str | None:
        self._rate_limit()
        try:
            resp = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            if resp.status_code == 404:
                logger.info('leetcode.ca 404: %s', url)
                return None
            resp.raise_for_status()
            return resp.text
        except requests.Timeout:
            logger.warning('Timeout fetching %s', url)
            return None
        except requests.RequestException as exc:
            logger.warning('Request error fetching %s: %s', url, exc)
            return None

    # ------------------------------------------------------------------
    # Stage 1 — parse /all/{id}.html
    # ------------------------------------------------------------------

    def _parse_page1(self, soup: BeautifulSoup, leetcode_id: int, page1_url: str) -> dict:
        """
        Extract from the old Bootstrap-style overview page:
          - title
          - problem description (from .markdown-body block)
          - solution page URL (from "Problem Solution" section)
        """
        result = {
            'title': '',
            'description': '',
            'solution_url': None,
        }

        # Title from <h1>N. Title Text</h1>
        h1 = soup.find('h1')
        if h1:
            raw = h1.get_text(strip=True)
            # Strip leading "N. " or "N - " prefix
            result['title'] = re.sub(r'^\d+[\.\-\s]+', '', raw).strip()

        # Problem description from <div class="markdown-body div-width">
        # This div contains the full problem statement paragraphs
        desc_div = soup.find('div', class_=lambda c: c and 'markdown-body' in c)
        if desc_div:
            # Collect meaningful text: paragraphs, lists, pre blocks
            # Exclude the Difficulty/Lock/Company metadata blocks at the bottom
            parts = []
            for child in desc_div.children:
                if not hasattr(child, 'name') or not child.name:
                    continue
                # Stop before the Difficulty / Lock / Company / Solution sections
                if child.name == 'div':
                    h3 = child.find('h3')
                    if h3 and h3.get_text(strip=True).lower() in (
                            'difficulty:', 'lock:', 'company:', 'problem solution', 'all problems:'):
                        break
                if child.name in ('h3',) and child.get_text(strip=True).lower() in (
                        'difficulty:', 'lock:', 'company:', 'problem solution', 'all problems:'):
                    break
                text = child.get_text(separator='\n', strip=True)
                if text:
                    parts.append(text)
            result['description'] = '\n\n'.join(parts).strip()

        # Solution link — find the <h3>Problem Solution</h3> and grab sibling <a>
        for heading in soup.find_all('h3'):
            if 'problem solution' in heading.get_text().lower():
                # The anchor is directly inside the parent <div> of the heading
                parent = heading.find_parent('div')
                if parent:
                    anchor = parent.find('a', href=True)
                    if anchor:
                        href = anchor['href']
                        # Make absolute URL; avoid re-linking to the /all/ page itself
                        if 'all/' not in href and href.startswith('http'):
                            result['solution_url'] = href
                        elif 'all/' not in href:
                            result['solution_url'] = urljoin(self.BASE_URL, href)
                break

        # Fallback: scan all anchors for the YYYY-MM-DD-{id}-slug pattern
        if not result['solution_url']:
            str_id = str(leetcode_id)
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Pattern: /YYYY-MM-DD-{id}-{slug} (not an /all/ link)
                if (
                    re.search(rf'/\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(str_id)}-', href)
                    and 'all/' not in href
                ):
                    result['solution_url'] = urljoin(self.BASE_URL, href)
                    break

        return result

    # ------------------------------------------------------------------
    # Stage 2 — parse the solution blog post
    # ------------------------------------------------------------------

    def _parse_page2(self, soup: BeautifulSoup) -> dict:
        """
        Extract from the Jekyll/UIKit solution blog post:
          - description (from <h1 id="question"> section, if present)
          - explanation (from <h1 id="algorithm"> section)
          - code (from UIKit tab switcher, prefer Python)
          - language
          - time_complexity / space_complexity
        """
        result = {
            'description': '',
            'explanation': '',
            'code': '',
            'language': 'python',
            'time_complexity': '',
            'space_complexity': '',
        }

        # ---- Description (Question / Description section) ----
        question_elem = (
            soup.find(['h1', 'h2', 'h3'], id=lambda x: x and any(w in x.lower() for w in ('question', 'description')))
            or soup.find(['h1', 'h2', 'h3'], string=lambda s: s and any(w in s.strip().lower() for w in ('question', 'description')))
        )
        if question_elem:
            result['description'] = _collect_siblings_until_heading(question_elem, stop_tags=('h1', 'h2'))

        # ---- Explanation (Algorithm section) ----
        algo_h1 = (
            soup.find(['h1', 'h2', 'h3'], id=lambda x: x and 'algorithm' in x.lower())
            or soup.find(['h1', 'h2', 'h3'], string=re.compile(r'^algorithm', re.I))
        )
        if algo_h1:
            result['explanation'] = _collect_siblings_until_heading(algo_h1, stop_tags=('h1', 'h2'))

        # ---- Code (UIKit tab/switcher) ----
        code_dict = self._extract_code_tabs(soup)
        code_by_language = {}
        if code_dict:
            for key, val in code_dict.items():
                k = key.lower()
                c_text = (val.get('code') or '').strip()
                if not c_text:
                    continue
                if 'python' in k:
                    code_by_language['python'] = c_text
                elif 'c++' in k or 'cpp' in k:
                    code_by_language['cpp'] = c_text
                elif 'java' in k and 'javascript' not in k:
                    code_by_language['java'] = c_text
                elif k == 'c' or 'c ' in k:
                    code_by_language['c'] = c_text

            preferred_order = ['python', 'java', 'c++', 'cpp', 'go', 'javascript']
            for pref in preferred_order:
                for key, val in code_dict.items():
                    if pref in key.lower():
                        result['code'] = val['code']
                        result['language'] = val['language']
                        # Extract complexities from the chosen code block
                        result['time_complexity'] = self._extract_complexity(
                            val['code'], 'time')
                        result['space_complexity'] = self._extract_complexity(
                            val['code'], 'space')
                        break
                if result['code']:
                    break
            # If still nothing, take the first available
            if not result['code'] and code_dict:
                first = next(iter(code_dict.values()))
                result['code'] = first['code']
                result['language'] = first['language']

        result['code_by_language'] = code_by_language

        # ---- Complexity fallback from full page text ----
        if not result['time_complexity'] or not result['space_complexity']:
            full_text = soup.get_text()
            if not result['time_complexity']:
                result['time_complexity'] = self._extract_complexity(full_text, 'time')
            if not result['space_complexity']:
                result['space_complexity'] = self._extract_complexity(full_text, 'space')

        return result

    def _extract_code_tabs(self, soup: BeautifulSoup) -> dict:
        """
        Extract code from UIKit tab/switcher pairs.

        Structure on Page 2:
            <ul class="uk-tab" data-uk-switcher="{connect:'#ID'}">
              <li class="uk-active"><a>Java</a></li>
              <li><a>C++</a></li>
              <li><a>Python</a></li>
              <li><a>Go</a></li>
            </ul>
            <ul id="ID" class="uk-switcher uk-margin">
              <li>  <-- Java code
                <div class="language-java highlighter-rouge">
                  <pre class="highlight"><code>...</code></pre>
                </div>
              </li>
              <li>  <-- C++ code
              ...
            </ul>

        Returns dict keyed by language label → {'code': str, 'language': str}
        """
        codes = {}

        tab_ul = soup.find('ul', class_=lambda c: c and 'uk-tab' in c)
        switcher_ul = soup.find('ul', class_=lambda c: c and 'uk-switcher' in c)

        if tab_ul and switcher_ul:
            tab_names = [li.get_text(strip=True) for li in tab_ul.find_all('li')]
            switcher_items = switcher_ul.find_all('li', recursive=False)

            for i, li in enumerate(switcher_items):
                tab_label = tab_names[i] if i < len(tab_names) else f'lang_{i}'
                code_text, lang = self._extract_code_from_li(li, tab_label)
                if code_text:
                    codes[tab_label.lower()] = {'code': code_text, 'language': lang}

        # Fallback: standalone pre/code blocks
        if not codes:
            for pre in soup.find_all('pre'):
                code_el = pre.find('code')
                text = (code_el or pre).get_text()
                if not self._looks_like_code(text):
                    continue
                classes = list(pre.get('class') or []) + list(
                    (code_el.get('class') if code_el else None) or []
                )
                lang = self._detect_language_from_classes(classes, text)
                if lang not in codes or len(text) > len(codes[lang]['code']):
                    codes[lang] = {'code': text.strip(), 'language': lang}

        return codes

    def _extract_code_from_li(self, li, tab_label: str) -> tuple[str, str]:
        """Extract plain code text and detected language from a switcher <li>."""
        # First try a language-specific div: <div class="language-python ...">
        lang_div = li.find('div', class_=re.compile(r'language-\w+'))
        if lang_div:
            classes = ' '.join(lang_div.get('class') or [])
            lang = self._detect_language_from_css_string(classes, tab_label)
            pre = lang_div.find('pre')
            if pre:
                code_el = pre.find('code')
                return (code_el or pre).get_text().strip(), lang

        # Fallback: any <pre> inside the <li>
        pre = li.find('pre')
        if pre:
            code_el = pre.find('code')
            code_text = (code_el or pre).get_text().strip()
            lang = self._detect_language_from_css_string(
                ' '.join(pre.get('class') or []), tab_label
            )
            return code_text, lang

        return '', 'python'

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def _detect_language_from_css_string(self, css_class_str: str, fallback_label: str = '') -> str:
        css = css_class_str.lower()
        if 'python' in css:
            return 'python'
        if 'java' in css and 'javascript' not in css:
            return 'java'
        if 'javascript' in css or 'js' in css:
            return 'javascript'
        if 'cpp' in css or 'c++' in css:
            return 'cpp'
        if 'go' in css or 'golang' in css:
            return 'go'
        if 'c' in css:
            return 'c'
        # Use the human-readable tab label as secondary signal
        return self._detect_language_from_label(fallback_label)

    def _detect_language_from_classes(self, classes: list, text: str) -> str:
        css = ' '.join(str(c) for c in classes).lower()
        lang = self._detect_language_from_css_string(css)
        if lang != 'python':   # trusts css detection
            return lang
        # Inspect code syntax as a tiebreaker
        return self._detect_language_from_syntax(text)

    def _detect_language_from_label(self, label: str) -> str:
        label = label.lower().strip()
        if 'python' in label or label == 'py':
            return 'python'
        if label in ('java',):
            return 'java'
        if label in ('c++', 'cpp'):
            return 'cpp'
        if label in ('go', 'golang'):
            return 'go'
        if 'javascript' in label or label == 'js':
            return 'javascript'
        return 'python'

    def _detect_language_from_syntax(self, text: str) -> str:
        if 'def ' in text and 'self' in text:
            return 'python'
        if 'public class' in text or 'System.out' in text:
            return 'java'
        if '#include' in text or 'std::' in text or 'vector<' in text:
            return 'cpp'
        if 'func ' in text and ('package ' in text or ':=' in text):
            return 'go'
        if 'function ' in text or 'const ' in text or 'let ' in text:
            return 'javascript'
        return 'python'

    # ------------------------------------------------------------------
    # Complexity extraction
    # ------------------------------------------------------------------

    def _extract_complexity(self, text: str, which: str) -> str:
        """Extract Time/Space complexity (O(…)) from code comments or prose."""
        patterns = [
            rf'//\s*{which}\s*[:\-]?\s*(O\([^)]+\))',      # // Time: O(N)
            rf'#\s*{which}\s*[:\-]?\s*(O\([^)]+\))',        # # Time: O(N)
            rf'{which}\s+complexity\s*[:\-]?\s*(O\([^)]+\))',
            rf'{which}\s*[:\-]\s*(O\([^)]+\))',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return ''

    # ------------------------------------------------------------------
    # Code heuristic
    # ------------------------------------------------------------------

    def _looks_like_code(self, text: str) -> bool:
        if not text or len(text) < 20:
            return False
        code_markers = (
            'class ', 'def ', 'function ', 'public ', 'private ', 'import ',
            'return ', 'for ', 'while ', 'if (', 'int ', 'void ', 'char ',
            'List[', 'vector<', 'HashMap', 'func ', 'package ', 'const ', '#include',
        )
        lines = text.split('\n')
        hits = sum(1 for ln in lines[:30] if any(ln.strip().startswith(m) for m in code_markers))
        return hits >= 2 or ('{' in text and '}' in text and ';' in text)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def scrape(self, leetcode_id: int) -> dict | None:
        """
        Full two-stage scrape pipeline.

        Returns a dict with:
            question_number, title, description, explanation, code,
            language, time_complexity, space_complexity,
            source_url (Page 1), solution_source_url (Page 2)

        Returns None on any unrecoverable failure.
        """
        if not leetcode_id:
            return None

        page1_url = self.ALL_URL_TEMPLATE.format(leetcode_id=leetcode_id)
        page1_html = self._fetch_html(page1_url)
        if not page1_html:
            logger.warning('Could not fetch Page 1 for problem #%d (%s)', leetcode_id, page1_url)
            return None

        page1_soup = BeautifulSoup(page1_html, 'html.parser')
        page1_data = self._parse_page1(page1_soup, leetcode_id, page1_url)

        logger.info(
            'Problem #%d — title=%r, solution_url=%r',
            leetcode_id, page1_data['title'], page1_data['solution_url'],
        )

        # Stage 2: fetch the dedicated solution page
        page2_data: dict = {}
        solution_source_url = page1_data['solution_url'] or ''

        if solution_source_url:
            page2_html = self._fetch_html(solution_source_url)
            if page2_html:
                page2_soup = BeautifulSoup(page2_html, 'html.parser')
                page2_data = self._parse_page2(page2_soup)
                logger.info(
                    'Problem #%d — code_lang=%r, expl_len=%d, code_len=%d',
                    leetcode_id,
                    page2_data.get('language'),
                    len(page2_data.get('explanation', '')),
                    len(page2_data.get('code', '')),
                )
            else:
                logger.warning(
                    'Could not fetch Page 2 for problem #%d (%s)',
                    leetcode_id, solution_source_url,
                )
        else:
            logger.warning('No solution URL found on Page 1 for problem #%d', leetcode_id)

        # Merge: Page 2 description is typically richer; fall back to Page 1 if missing
        description = page2_data.get('description') or page1_data.get('description', '')
        title = page1_data.get('title') or f'LeetCode {leetcode_id}'

        parsed = parse_structured_statement(description)
        clean_desc = parsed.get('description') or description or 'Problem description not available.'

        return {
            'question_number': leetcode_id,
            'title': title,
            'description': clean_desc,
            'examples': parsed.get('examples') or [],
            'constraints': parsed.get('constraints') or [],
            'explanation': page2_data.get('explanation') or 'Solution explanation not available.',
            'solution': page2_data.get('explanation') or '',   # alias kept for compatibility
            'code': page2_data.get('code') or '# Solution code not available for this problem.',
            'code_by_language': page2_data.get('code_by_language') or {},
            'language': page2_data.get('language') or 'python',
            'time_complexity': page2_data.get('time_complexity') or '',
            'space_complexity': page2_data.get('space_complexity') or '',
            'source_url': page1_url,                           # Page 1 (overview)
            'solution_source_url': solution_source_url,        # Page 2 (solution blog)
        }


# ---------------------------------------------------------------------------
# Module-level singleton + public API
# ---------------------------------------------------------------------------

_scraper = LeetCodeCaScraper()


def fetch_solution(leetcode_id: int) -> dict | None:
    """
    Public API: fetch and parse a structured solution from leetcode.ca.
    Returns a structured dict or None on failure.
    """
    if not leetcode_id:
        return None
    return _scraper.scrape(leetcode_id)