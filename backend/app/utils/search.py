from duckduckgo_search import DDGS

def search_the_web(query: str) -> str:
    """
    Perform a search query on DuckDuckGo and return formatted text results
    with top 3 snippets for the AI to use as context.
    """
    try:
        print(f"[SEARCH UTILITY] Running DuckDuckGo search for: '{query}'")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if not results:
                return "\n\n--- WEB SEARCH RESULTS ---\nNo search results found on the web.\n---------------------------\n"
            
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
        print(f"[SEARCH UTILITY] Error during search: {e}")
        return f"\n\n--- WEB SEARCH FAILED ---\nCould not retrieve web results: {e}\n---------------------------\n"
