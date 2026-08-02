from duckduckgo_search import DDGS

def search_the_web(query: str) -> str:
    """
    Perform a search query on DuckDuckGo and return formatted text results
    with top 3 snippets for the AI to use as context.
    """
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
