import urllib.request
import urllib.parse
import re
from duckduckgo_search import DDGS

def fallback_urllib_search(query: str) -> list[dict]:
    """
    Direct urllib-based scraper for duckduckgo.com HTML search page.
    Used as a fallback if the third-party library is blocked or returns empty.
    """
    try:
        print(f"[SEARCH UTILITY] Running fallback urllib search for: '{query}'")
        url = "https://html.duckduckgo.com/html/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8", errors="ignore")
            
        results = []
        blocks = html_content.split('class="result')
        for block in blocks[1:]:  # Skip the first block before the first result
            a_match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
            snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
            
            if a_match and snippet_match:
                href = a_match.group(1)
                # Clean href if it is a DDG redirect, e.g., //duckduckgo.com/l/?uddg=URL
                if "uddg=" in href:
                    try:
                        parsed_href = urllib.parse.urlparse(href)
                        query_params = urllib.parse.parse_qs(parsed_href.query)
                        if "uddg" in query_params:
                            href = query_params["uddg"][0]
                    except Exception as parse_err:
                        print(f"[SEARCH UTILITY] Error parsing redirect URL: {parse_err}")
                
                # Strip HTML tags from title and snippet
                title = re.sub(r'<[^>]+>', '', a_match.group(2)).strip()
                body = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                
                if title and body:
                    results.append({
                        "title": title,
                        "href": href,
                        "body": body
                    })
                    if len(results) >= 3:
                        break
        print(f"[SEARCH UTILITY] Fallback urllib search completed. Found {len(results)} results.")
        return results
    except Exception as e:
        print(f"[SEARCH UTILITY] Fallback urllib search failed: {e}")
        return []

def search_the_web(query: str) -> str:
    """
    Perform a search query on DuckDuckGo and return formatted text results
    with top 3 snippets for the AI to use as context.
    """
    # Clean the query to improve search results accuracy on DuckDuckGo.
    # Replace "current weather" with just "weather", and remove the word "current".
    query = re.sub(r'\bcurrent weather\b', 'weather', query, flags=re.IGNORECASE)
    query = re.sub(r'\bcurrent\b', '', query, flags=re.IGNORECASE).strip()
    query = re.sub(r'\s+', ' ', query)

    backends = ["lite", "html"]
    results = None
    last_err = None
    
    # Try different backends (lite first as it is less blocked on cloud servers)
    for backend in backends:
        try:
            print(f"[SEARCH UTILITY] Trying DuckDuckGo search (backend='{backend}') for: '{query}'")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, backend=backend, max_results=3))
                if results:
                    print(f"[SEARCH UTILITY] Search succeeded using backend='{backend}' with {len(results)} results.")
                    break
        except Exception as e:
            print(f"[SEARCH UTILITY] Backend '{backend}' failed: {e}")
            last_err = e
            
    # If no results found using specific backends, try default auto
    if not results:
        try:
            print(f"[SEARCH UTILITY] Trying default DuckDuckGo search (auto) for: '{query}'")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    print(f"[SEARCH UTILITY] Search succeeded using auto backend with {len(results)} results.")
        except Exception as e:
            print(f"[SEARCH UTILITY] Auto backend failed: {e}")
            last_err = e

    # Fallback to custom urllib scraper if ddgs library failed or returned empty results
    if not results:
        results = fallback_urllib_search(query)

    try:
        if not results:
            err_info = f" (Error: {last_err})" if last_err else ""
            return f"\n\n--- WEB SEARCH RESULTS ---\nNo search results found on the web{err_info}.\n---------------------------\n"
        
        formatted_results = []
        for r in results:
            title = r.get("title", "No Title")
            body = r.get("body", "")
            href = r.get("href", "")
            formatted_results.append(f"- **{title}**\n  Snippet: {body}\n  Link: {href}")
        
        context = (
            "\n\n--- WEB SEARCH RESULTS ---\n"
            "The following real-time web search results were found for this query. "
            "Use them to provide an accurate, up-to-date response:\n"
            + "\n\n".join(formatted_results)
            + "\n---------------------------\n"
        )
        return context
    except Exception as e:
        print(f"[SEARCH UTILITY] Error formatting results: {e}")
        return f"\n\n--- WEB SEARCH FAILED ---\nCould not format web results: {e}\n---------------------------\n"
