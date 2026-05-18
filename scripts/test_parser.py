import sys, os, re
sys.path.insert(0, os.path.abspath("."))
from bs4 import BeautifulSoup

html = """<!DOCTYPE html>
<html><body class="path-mod-assign">
<h2>Test</h2>
<div class="box">
  <div class="box-header"><h3>Condições de conclusão</h3></div>
  <div class="box-content">
    <p><strong>Aberto:</strong> quarta-feira, 13 mai. 2026, 21:00</p>
    <p><strong>Conclusão:</strong> quarta-feira, 3 jun. 2026, 23:59</p>
  </div>
</div>
</body></html>"""

soup = BeautifulSoup(html, "lxml")
text = soup.text

# Direct regex test
label = "Conclusão"
pattern = label + r"[:\s]*(?:[a-zA-ZÀ-ÿ]+,?\s*)?\d{1,2}(?:\s+[a-z]{3,4}\.?\s+|\s+de\s+\w+\s+|[/-])\d{2,4},?\s+\d{1,2}:\d{2}"
compiled = re.compile(pattern, re.I)

print("Testing regex on:", repr(text))
print("Pattern:", pattern)
print()

# Find all matches
for m in compiled.finditer(text):
    print(f"MATCH: '{m.group(0)[:80]}' at pos {m.start()}")

if not list(compiled.finditer(text)):
    print("NO MATCHES!")
    # Test just the label
    print(f"\nContains 'Conclusão': {'Conclusão' in text}")
    print(f"Contains 'Conclusão:': {'Conclusão:' in text}")
    
    # Step by step
    for m in re.finditer(re.escape(label), text, re.I):
        print(f"\nFound '{m.group()}' at pos {m.start()}, context: '{text[m.start():m.start()+80]}'")

# Also test with the exact combined regex
from src.scraper.html_parser import MoodleHTMLParser
parser = MoodleHTMLParser()
print(f"\nParser result: {parser._extract_due_date(soup)}")
