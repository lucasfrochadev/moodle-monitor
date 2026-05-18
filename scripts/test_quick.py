import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.scraper.html_parser import MoodleHTMLParser
from bs4 import BeautifulSoup

html = """<!DOCTYPE html>
<html><body class="path-mod-assign">
<h2>B2 - Site com BACKEND em PHP</h2>
<div class="box">
  <div class="box-header"><h3>Condi\u00e7\u00f5es de conclus\u00e3o</h3></div>
  <div class="box-content">
    <p><strong>Aberto:</strong> quarta-feira, 13 mai. 2026, 21:00</p>
    <p><strong>Conclus\u00e3o:</strong> quarta-feira, 3 jun. 2026, 23:59</p>
  </div>
</div>
</body></html>"""

soup = BeautifulSoup(html, "lxml")
parser = MoodleHTMLParser()
due = parser._extract_due_date(soup)
open_dt = parser._extract_open_date(soup)
print(f"Due: {due}")
print(f"Open: {open_dt}")
print(f"Text: {repr(soup.text[:200])}")
