import urllib.request
import re
from bs4 import BeautifulSoup

def inspect_page(number):
    url = f"https://leetcode.ca/all/{number}.html"
    print(f"\n==================== INSPECTING {url} ====================")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            print("Status: 200 | HTML length:", len(html))
            soup = BeautifulSoup(html, 'html.parser')
            print("Page Title:", soup.title.get_text() if soup.title else None)
            
            # Print headings
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            print("Headings:", [f"{h.name}: {h.get_text(strip=True)}" for h in headings])
            
            # Print all links on the page
            links = soup.find_all('a')
            print(f"Total links: {len(links)}")
            for a in links:
                txt = a.get_text(strip=True)
                href = a.get('href')
                if href and not href.startswith('#') and not href.startswith('javascript'):
                    print(f"  Link: text='{txt}' | href='{href}'")
            
            # Check pre / code blocks
            pre_blocks = soup.find_all('pre')
            print(f"Total <pre> blocks: {len(pre_blocks)}")
            for i, p in enumerate(pre_blocks):
                code_tag = p.find('code')
                cls = p.get('class', []) + (code_tag.get('class', []) if code_tag else [])
                text_sample = p.get_text()[:120].replace('\n', ' ')
                print(f"  Pre #{i} class={cls}: {text_sample}...")
                
            # Check paragraphs or content containers
            article = soup.find('article') or soup.find('main') or soup.find(class_=re.compile(r'content|post|entry'))
            if article:
                print("Container tag:", article.name, "classes:", article.get('class'))
                # Print direct children tags
                children = [c.name for c in article.children if c.name]
                print("Children tags in container:", children[:15])
            else:
                print("No article/main container found")

    except Exception as e:
        print("Error fetching:", e)

inspect_page(158)
inspect_page(1)
inspect_page(200)
