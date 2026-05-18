import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.scraper.html_parser import MoodleHTMLParser
from bs4 import BeautifulSoup

html = (
    '<!DOCTYPE html>\n'
    '<html><body class="path-mod-forum">\n'
    '<h2>F2 - plataformas de ensino</h2>\n'
    '<div class="box">\n'
    '  <div class="box-header"><h3>Condi\u00e7\u00f5es de conclus\u00e3o</h3></div>\n'
    '  <div class="box-content">\n'
    '    <p><strong>Conclus\u00e3o:</strong> segunda-feira, 18 mai. 2026, 22:40</p>\n'
    '  </div>\n'
    '</div>\n'
    '</body></html>'
)

soup = BeautifulSoup(html, "lxml")
parser = MoodleHTMLParser()
due = parser._extract_due_date(soup)
print(f"Due: {due}")
print(f"Text: {repr(soup.text)}")
