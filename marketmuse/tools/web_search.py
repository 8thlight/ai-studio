from pydantic import BaseModel, Field
from typing_extensions import List
import logging
import requests
from autogen_core import TRACE_LOGGER_NAME
from bs4 import BeautifulSoup
from googlesearch import search

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(TRACE_LOGGER_NAME)

class SearchOutput(BaseModel):
    title: str = Field(title="title", description="The title of a search result")
    link: str = Field(title="link", description="The link to the search result")
    snippet: str = Field(title="snippet", description="The snippet displayed within the search result")
    body: str = Field(
        title="body", description="The body of the page linked to the search result. Parsed and presented as raw text"
    )

def web_search(queries: List[str]) -> List[SearchOutput]:
    # Execute a web search for each query passed and returns a list of {SearchOutput}
    num_results = 5
    all_results = []
    logger.debug(f"SEARCHING THROUGH QUERIES: {queries}")
    for query in queries:
        try:
            logger.debug(f"SEARCHING FOR: {query}")
            results = search(query, num_results=num_results, advanced=True, lang="en", region="us")
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"An error occurred during search: {e}")

    enriched_results = []
    for result in all_results:
        if result.url == "/search?num=7": continue  # when a google search returns a "searching for" then that will count as a link which is broken
        url = result.url
        try:
            body = _get_page_content(url)
            enriched_results.append(
                SearchOutput(
                    title=result.title,
                    link=url,
                    body=body,
                    snippet=result.description,
                )
            )
        except Exception as e:
            logger.warning(f"AN ERROR OCCURRED WHILE PARSING PAGE CONTENT for {result.url}::: {e}")
    return enriched_results


def _get_page_content(url: str) -> str:
    max_chars_from_page_body = 5000
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        words = text.split()
        content = ""
        for word in words:
            if len(content) + len(word) + 1 > max_chars_from_page_body:
                break
            content += " " + word
        return content.strip()
    except Exception as e:
        logger.warning(f"Error fetching {url}: {str(e)}")
        return ""
