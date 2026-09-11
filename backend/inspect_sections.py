import urllib.request
from bs4 import BeautifulSoup

url = 'https://leetcode.ca/2016-05-06-158-Read-N-Characters-Given-Read4-II-Call-multiple-times/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    soup = BeautifulSoup(resp.read(), 'html.parser')
    
    for h in soup.find_all('h1'):
        text = h.get_text(strip=True)
        print('=== Section:', text, '===')
        curr = h.find_next_sibling()
        count = 0
        while curr and curr.name != 'h1' and count < 5:
            sample = curr.get_text()[:80].replace('\n', ' ').strip()
            print(f"  <{curr.name} class={curr.get('class')}>: {sample}")
            curr = curr.find_next_sibling()
            count += 1
