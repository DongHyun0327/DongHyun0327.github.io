from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean_text(value):
    if not value:
        return ""
    return " ".join(value.strip().split())


def make_job(title, company, link, source):
    return {
        "title": clean_text(title) or "No title",
        "company": clean_text(company) or "Unknown company",
        "link": link,
        "source": source,
    }


def scrape_berlinstartupjobs(keyword):
    url = f"https://berlinstartupjobs.com/skill-areas/{keyword.lower()}/"
    soup = get_soup(url)
    jobs = []
    seen = set()

    for title_tag in soup.select("h4 a"):
        title = clean_text(title_tag.get_text())
        link = title_tag.get("href", "")
        if not title or not link:
            continue

        company = "Unknown company"
        parent = title_tag.parent
        if parent:
            next_company = parent.find_next("a")
            if next_company and next_company != title_tag:
                company = clean_text(next_company.get_text())

        job_key = (title, company, link)
        if job_key in seen:
            continue
        seen.add(job_key)
        jobs.append(make_job(title, company, link, "Berlin Startup Jobs"))

    return jobs


def scrape_weworkremotely(keyword):
    url = f"https://weworkremotely.com/remote-jobs/search?utf8=%E2%9C%93&term={keyword}"
    soup = get_soup(url)
    jobs = []
    seen = set()

    for section in soup.select("section.jobs"):
        for job in section.select("li"):
            classes = job.get("class", [])
            if "view-all" in classes or "load_more" in classes:
                continue

            link_tag = job.select_one("a[href]")
            title_tag = job.select_one(".title, span[title], .new-listing__header__title")
            company_tag = job.select_one(".company, .new-listing__company-name")

            if not link_tag or not title_tag:
                continue

            link = link_tag.get("href", "")
            if link.startswith("/"):
                link = f"https://weworkremotely.com{link}"

            title = clean_text(title_tag.get_text())
            company = clean_text(company_tag.get_text()) if company_tag else "Unknown company"

            if not title or not link:
                continue

            job_key = (title, company, link)
            if job_key in seen:
                continue
            seen.add(job_key)
            jobs.append(make_job(title, company, link, "We Work Remotely"))

    return jobs


def scrape_web3(keyword):
    url = f"https://web3.career/{keyword.lower()}-jobs"
    soup = get_soup(url)
    jobs = []
    seen = set()

    table = soup.select_one("table")
    if not table:
        return jobs

    rows = table.select("tr")
    for row in rows:
        links = row.select("a[href]")
        if len(links) < 2:
            continue

        title = clean_text(links[0].get_text())
        company = clean_text(links[1].get_text())
        link = links[0].get("href", "")

        if not title or not company or not link:
            continue

        if link.startswith("/"):
            link = f"https://web3.career{link}"

        job_key = (title, company, link)
        if job_key in seen:
            continue
        seen.add(job_key)
        jobs.append(make_job(title, company, link, "Web3 Career"))

    return jobs


def get_jobs(keyword):
    jobs = []
    jobs.extend(scrape_berlinstartupjobs(keyword))
    jobs.extend(scrape_weworkremotely(keyword))
    jobs.extend(scrape_web3(keyword))
    return jobs


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/search")
def search():
    keyword = clean_text(request.args.get("keyword", ""))
    if not keyword:
        return render_template("search.html", keyword=keyword, jobs=[])

    try:
        jobs = get_jobs(keyword)
        error = None
    except requests.RequestException:
        jobs = []
        error = "채용 정보를 불러오는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."

    return render_template("search.html", keyword=keyword, jobs=jobs, error=error)


if __name__ == "__main__":
    app.run()
