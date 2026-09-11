import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def test_full_flow(number):
    all_url = f"https://leetcode.ca/all/{number}.html"
    print(f"\n=================== TESTING #{number} ===================")
    req = urllib.request.Request(all_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            # Look for solution link
            solution_link = None
            # Check links that have /{number}- in href or match date pattern
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if f"-{number}-" in href or href.endswith(f"-{number}") or f"/{number}-" in href:
                    solution_link = urljoin(all_url, href)
                    break
            
            print(f"Step 1: {all_url} -> Solution Link: {solution_link}")
            
            target_url = solution_link if solution_link else all_url
            req2 = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                soup2 = BeautifulSoup(resp2.read(), 'html.parser')
                
                # Check Algorithm / Explanation
                algo_section = []
                for h1 in soup2.find_all('h1'):
                    if 'Algorithm' in h1.get_text():
                        curr = h1.find_next_sibling()
                        while curr and curr.name not in ['h1', 'h2']:
                            algo_section.append(curr.get_text(separator=' ', strip=True))
                            curr = curr.find_next_sibling()
                
                # Check Question Description
                desc_section = []
                for h1 in soup2.find_all('h1'):
                    if 'Question' in h1.get_text():
                        curr = h1.find_next_sibling()
                        while curr and curr.name not in ['h1', 'h2']:
                            t = curr.get_text(separator=' ', strip=True)
                            if 'Formatted question description' not in t:
                                desc_section.append(t)
                            curr = curr.find_next_sibling()
                            
                # Check Code tabs and switchers
                tabs = []
                tab_ul = soup2.find('ul', class_=lambda c: c and 'uk-tab' in c)
                if tab_ul:
                    tabs = [li.get_text(strip=True) for li in tab_ul.find_all('li')]
                
                codes = {}
                switcher_ul = soup2.find('ul', class_=lambda c: c and 'uk-switcher' in c)
                if switcher_ul:
                    lis = switcher_ul.find_all('li', recursive=False)
                    for i, li in enumerate(lis):
                        lang = tabs[i] if i < len(tabs) else f"lang_{i}"
                        pre = li.find('pre')
                        codes[lang] = pre.get_text(strip=True) if pre else li.get_text(strip=True)
                else:
                    # Fallback: find all pre blocks
                    for i, pre in enumerate(soup2.find_all('pre')):
                        codes[f'code_{i}'] = pre.get_text(strip=True)
                        
                print("Step 2: Extracted Data:")
                print("  Description lines:", len(desc_section), "Sample:", desc_section[0][:100] if desc_section else "None")
                print("  Algorithm lines:", len(algo_section), "Sample:", algo_section[0][:100] if algo_section else "None")
                print("  Code languages available:", list(codes.keys()))
                for lang, code_sample in codes.items():
                    print(f"    {lang}: {len(code_sample)} chars | {code_sample[:60].replace(chr(10), ' ')}...")

    except Exception as e:
        print("Error:", e)

test_full_flow(158)
test_full_flow(1)
test_full_flow(200)
