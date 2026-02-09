import requests
from urllib.parse import quote

def shorten_url(long_url):
    """
    Tries to shorten the URL using ulvis.net. 
    If it fails, returns the original URL.
    """
    # Ulvis is generally more relaxed with Cloudflare tunnel links
    api_url = f"https://ulvis.net/api.php?url={quote(long_url)}"
    
    try:
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200 and "ulvis.net" in response.text:
            short_url = response.text.strip()
            return short_url
        else:
            # If Ulvis also fails, we just give up and use the long one
            return long_url
            
    except Exception:
        return long_url

if __name__ == "__main__":
    test_url = "https://example.trycloudflare.com"
    print(f"Testing with: {test_url}")
    print(f"Result: {shorten_url(test_url)}")