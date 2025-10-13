# main/list_from_db.py
import os, sys, re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

#Django setup
#ROOT = Path(__file__).resolve().parents[1]
#sys.path.insert(0, str(ROOT))
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Capstone.settings")
import django
#django.setup()

from main.models import Course
from main.csce_scraper import build_term_codes_past_years

#DB helper
CSCE_RE = re.compile(r'^CSCE\s*A\d{3}[A-Z]?$')

def get_csce_courses_past_5y():
    terms = [t for t, _ in build_term_codes_past_years(years=5)]
    qs = (Course.objects
          .filter(term__in=terms)
          .values_list("code", flat=True)
          .distinct())
    return sorted({(c or "").strip() for c in qs if c and CSCE_RE.fullmatch((c or "").strip())})

#Prerequisite scraper
#REGEX patterns
SUBJECT_URL  = "https://catalog.uaa.alaska.edu/coursedescriptions/csce/"
CSCE_CODE_RE = re.compile(r'\bCSCE\s*A\d{3}[A-Z]?\b', re.IGNORECASE)
PREREQ_SENT  = re.compile(r'Prerequisite(?:s)?\s*:\s*(.+?)(?:\.\s|$)', re.IGNORECASE | re.DOTALL)
DIGITS       = re.compile(r'\d{3}')

#cleans the text
def norm(s):
    return re.sub(r'\s+', ' ', (s or '').replace('\xa0', ' ')).strip()

#gets the numeric portion (e.g. 201)
def num(code):
    m = DIGITS.search(code or '')
    return int(m.group()) if m else -1

#checks if it's in the range 100-400 course level
def in_course_range(code):
    n = num(code)
    return 100 <= n < 500

def pick_two(course, direct):
    picked, seen = [], set()
    #direct first
    for d in direct.get(course, []):
        if d not in seen:
            seen.add(d)
            picked.append(d)
            if len(picked) == 2:
                return sorted(picked, key=num, reverse=True)
    #then one-hop
    for d in direct.get(course, []):
        for dd in direct.get(d, []):
            if dd != course and dd not in seen and in_course_range(dd):
                seen.add(dd)
                picked.append(dd)
                if len(picked) == 2:
                    return sorted(picked, key=num, reverse=True)
    return sorted(picked, key=num, reverse=True)

def build_two_prereq_map():
    html = requests.get(SUBJECT_URL, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    #course -> text (100–400 only)
    blocks = {}
    for blk in soup.select(".courseblock"):
        txt = norm(blk.get_text(" ", strip=True))
        m = CSCE_CODE_RE.search(txt)
        if not m:
            continue
        code = norm(m.group(0))
        if in_course_range(code):
            blocks[code] = txt

    #direct prereqs from prerequisite(s)
    direct = {}
    for c in blocks:
        direct[c] = []
    for code, text in blocks.items():
        prereq_text = " ".join(norm(m.group(1)) for m in PREREQ_SENT.finditer(text))
        tokens = []
        for t in CSCE_CODE_RE.findall(prereq_text):
            clean_t = norm(t)
            tokens.append(clean_t)
        seen, out = set(), []
        for t in tokens:
            if t != code:                 #not the same course
                if t not in seen:         #not a duplicate
                    if in_course_range(t):  #is 100–400 level
                        seen.add(t)
                        out.append(t)
        direct[code] = out

    final = {}
    for c in blocks:
        final[c] = pick_two(c, direct)

    #override for 470
    if "CSCE A470" in final:
        final["CSCE A470"] = ["CSCE A401", "CSCE A351"]

    return final

#main
if __name__ == "__main__":
    data = build_two_prereq_map()
    saved_count = Prerequisite.save_prereq_data(data)
    print(f"Saved {saved_count} prerequisites to DB.")

"""
if __name__ == "__main__":
    courses = get_csce_courses_past_5y()
    two_map = build_two_prereq_map()
    course_to_prereqs = {c: two_map.get(c.strip(), []) for c in courses}

    for course, prereqs in course_to_prereqs.items():
        print(f"{course}: {prereqs}")
"""