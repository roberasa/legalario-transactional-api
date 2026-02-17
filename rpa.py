import requests
from playwright.sync_api import sync_playwright

API_URL = "http://localhost:8000/assistant/summarize"


def run_rpa(search_term: str):
    """
    Opens Wikipedia, searches a term,
    extracts the first paragraph,
    sends it to our API for AI summarization.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to Wikipedia
        page.goto("https://www.wikipedia.org/")

        # Search
        page.fill("input[name='search']", search_term)
        page.press("input[name='search']", "Enter")

        page.wait_for_selector("p")

        paragraphs = page.query_selector_all("p")

        first_paragraph = ""
        for p in paragraphs:
            text = p.inner_text().strip()
            if text:
                first_paragraph = text
                break

        browser.close()

    if not first_paragraph:
        print("No paragraph found.")
        return

    print("\n📄 Extracted Text:\n")
    print(first_paragraph)

    # Send to your API
    response = requests.post(API_URL, json={
        "text": first_paragraph
    })

    print("\n🤖 AI Summary Response:\n")
    print(response.json())


if __name__ == "__main__":
    term = input("Enter a search term for Wikipedia: ")
    run_rpa(term)
