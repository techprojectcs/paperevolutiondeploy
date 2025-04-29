from flask import Flask, render_template, request, session, send_file, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import xml.etree.ElementTree as ET
import asyncio
from collections import Counter
import requests
import aiohttp
import asyncio
import httpx
import csv
import io
import json
import os

import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')  # path to your key
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://realtime-database-b7cd9-default-rtdb.firebaseio.com/'
})


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- User Utilities ---
# --- Firebase Utilities ---

def load_users():
    ref = db.reference('users')
    users = ref.get()
    return users if users else []

def save_users(users):
    ref = db.reference('users')
    ref.set(users)

def find_user(username):
    users = load_users()
    for user in users:
        if user['username'] == username:
            return user
    return None


def sanitize_username(username):
    return username.replace('.', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')

def load_bookmarks(username):
    ref = db.reference(f'bookmarks/{sanitize_username(username)}')
    bookmarks = ref.get()
    return bookmarks if bookmarks else []

def save_bookmarks(username, bookmarks):
    ref = db.reference(f'bookmarks/{sanitize_username(username)}')
    ref.set(bookmarks)


# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keywords = request.form['keywords']
        year = request.form.get('year', '')
        author = request.form.get('author', '')
        session['keywords'] = keywords
        session['year'] = year
        session['author'] = author
        return redirect(url_for('results', page=1))
    return render_template('index.html', current_year=datetime.now().year)

@app.route('/bookmarks')
def bookmarks():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    user_bookmarks = load_bookmarks(username)
    return render_template('bookmarks.html', bookmarks=user_bookmarks)

@app.route('/bookmark', methods=['POST'])
def bookmark():
    if 'user' not in session:
        return jsonify({"message": "Login required to bookmark."}), 401

    paper = request.get_json()
    username = session['user']
    bookmarks = load_bookmarks(username)

    if not any(b['title'].lower() == paper['title'].lower() for b in bookmarks):
        bookmarks.append(paper)
        save_bookmarks(username, bookmarks)
        return jsonify({"message": "Paper bookmarked successfully!"})
    return jsonify({"message": "Paper already bookmarked."})

@app.route('/delete_bookmark', methods=['POST'])
def delete_bookmark():
    if 'user' not in session:
        return jsonify({"message": "Login required to delete bookmark."}), 401

    data = request.get_json()
    title_to_delete = data.get('title')
    username = session['user']

    bookmarks = load_bookmarks(username)
    bookmarks = [b for b in bookmarks if b['title'].lower() != title_to_delete.lower()]
    save_bookmarks(username, bookmarks)

    return jsonify({"message": "Bookmark deleted successfully!"})

@app.route('/delete_all_bookmarks', methods=['POST'])
def delete_all_bookmarks():
    if 'user' not in session:
        return jsonify({"message": "Login required."}), 401

    username = session['user']
    save_bookmarks(username, [])
    return jsonify({"message": "All bookmarks deleted!"})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if find_user(username):
            return render_template('register.html', error='Username already exists')

        users = load_users()
        users.append({
            'username': username,
            'password': generate_password_hash(password),
            'bookmarks': []
        })
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = find_user(username)
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# --- API Configuration ---
RESULTS_PER_PAGE = 50
MAX_RESULTS = 200
MAX_OFFSET = MAX_RESULTS // RESULTS_PER_PAGE

API_KEYS = {
}

# --- Async Utilities ---
async def fetch_with_timeout(url, headers=None):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}")
        return None
    

# --- Source Fetchers ---


async def fetch_from_openalex(keywords, year, author, offset):
    url = f"https://api.openalex.org/works?search={keywords}&per-page={RESULTS_PER_PAGE}&page={offset+1}"
    data = await fetch_with_timeout(url)
    papers = []
    if data and "results" in data:
        for item in data["results"]:
            papers.append({
                "title": item.get("title", ""),
                "authors": ", ".join([auth.get("author", {}).get("display_name", "") for auth in item.get("authorships", [])]),
                "abstract": item.get("abstract", ""),
                "url": item.get("id"),
                "source": "OpenAlex",
                "publisher": "OpenAlex",
                "year": item.get("publication_year")
            })
    return papers

async def fetch_from_crossref(keywords, year, author, offset):
    base_url = "https://api.crossref.org/works"
    params = {
        "query": keywords,
        "rows": RESULTS_PER_PAGE,
        "offset": offset * RESULTS_PER_PAGE
    }
    if year:
        params["filter"] = f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31"
    if author:
        params["query.author"] = author

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{base_url}?{query}"
    data = await fetch_with_timeout(url)
    papers = []
    if data and "message" in data and "items" in data["message"]:
        for item in data["message"]["items"]:
            papers.append({
                "title": item.get("title", [""])[0],
                "authors": ", ".join(a.get("given", "") + " " + a.get("family", "") for a in item.get("author", [])),
                "abstract": item.get("abstract", ""),
                "url": item.get("URL"),
                "source": "Crossref",
                "publisher": "Crossref",
                "year": item.get("issued", {}).get("date-parts", [[""]])[0][0] if item.get("issued") else None
            })
    return papers

async def fetch_from_europepmc(keywords, year, author, offset):
    query = keywords
    if year:
        query += f" AND PUB_YEAR:{year}"
    if author:
        query += f" AND AUTH:{author}"
    
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize={RESULTS_PER_PAGE}&page={offset+1}"
    data = await fetch_with_timeout(url)
    
    papers = []
    if data and "resultList" in data and "result" in data["resultList"]:
        for item in data["resultList"]["result"]:
            full_text_url = ""
            
            # Check for full-text open access URLs
            if "fullTextUrlList" in item and "fullTextUrl" in item["fullTextUrlList"]:
                for entry in item["fullTextUrlList"]["fullTextUrl"]:
                    if entry.get("availability") == "Open access" and entry.get("documentStyle") in ["html", "pdf"]:
                        full_text_url = entry.get("url", "")
                        break
            
            # If no open access link found, build fallback Europe PMC article page
            if not full_text_url:
                if "doi" in item:
                    full_text_url = f"https://europepmc.org/article/DOI/{item['doi']}"
                elif "pmcid" in item:
                    full_text_url = f"https://europepmc.org/article/PMC/{item['pmcid']}"
                elif "id" in item and "source" in item:
                    full_text_url = f"https://europepmc.org/article/{item['source']}/{item['id']}"

            papers.append({
                "title": item.get("title", "No Title"),
                "authors": item.get("authorString", "Unknown"),
                "abstract": item.get("abstractText", "No abstract available"),
                "url": full_text_url,
                "source": "Europe PMC",
                "publisher": item.get("journalTitle", "Unknown"),
                "year": item.get("pubYear", "Unknown")
            })
    
    return papers


async def fetch_from_arxiv(keywords, year, author, offset):
    start = offset * RESULTS_PER_PAGE
    url = f"http://export.arxiv.org/api/query?search_query=all:{keywords}&start={start}&max_results={RESULTS_PER_PAGE}"
    text_data = await fetch_with_timeout(url)
    papers = []
    if text_data:
        root = ET.fromstring(text_data)
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text
            authors = ", ".join([author.find('{http://www.w3.org/2005/Atom}name').text for author in entry.findall('{http://www.w3.org/2005/Atom}author')])
            link = entry.find('{http://www.w3.org/2005/Atom}id').text
            year_text = entry.find('{http://www.w3.org/2005/Atom}published').text[:4]
            papers.append({
                "title": title,
                "authors": authors,
                "abstract": summary,
                "url": link,
                "source": "ArXiv",
                "year": year_text,
                "publisher": "ArXiv"
            })
    return papers

import urllib.parse

async def fetch_from_doaj(keywords, year=None, author=None, offset=0):
    page = offset   # DOAJ pages are 1-based
    query = f'bibjson.keywords:"{keywords}"'
    if author:
        query += f' AND bibjson.author.name:"{author}"'
    if year:
        query += f' AND bibjson.year:{year}'

    encoded_query = urllib.parse.quote(query)
    url = f"https://doaj.org/api/v2/search/articles/{encoded_query}?page={page}&pageSize={RESULTS_PER_PAGE}"

    papers = []

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Error fetching from DOAJ: {response.status}")
                    return []
                data = await response.json()
        except Exception as e:
            print(f"Exception during DOAJ fetch: {e}")
            return []

    for article in data.get('results', []):
        bibjson = article.get('bibjson', {})
        title = bibjson.get('title', 'No Title Available')
        abstract = bibjson.get('abstract', 'No abstract available')

        authors_data = bibjson.get('author', [])
        authors_list = [a.get('name', '') for a in authors_data]
        authors_string = ", ".join(authors_list) if authors_list else "Unknown Author"

        year_text = bibjson.get('year', 'Unknown Year')

        link = bibjson.get('link', [])
        link_url = link[0].get('url') if link else article.get('id', '#')

        papers.append({
            "title": title,
            "authors": authors_string,
            "abstract": abstract,
            "url": link_url,
            "source": "DOAJ",
            "year": year_text,
            "publisher": "DOAJ"
        })

    return papers

async def fetch_with_timeouts(session, url, payload, headers, timeout=5):
    try:
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"IEEE Xplore error: Status {response.status}")
                return None
    except Exception as e:
        print(f"Exception during IEEE fetch: {e}")
        return None

async def fetch_from_ieee_xplore(keywords, year=None, author=None, offset=0):
    search_url = "https://ieeexplore.ieee.org/rest/search"
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://ieeexplore.ieee.org/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
    }

    page = offset  # IEEE pagination is 1-based
    payload = {
        "queryText": keywords,
        "highlight": True,
        "returnType": "SEARCH",
        "rowsPerPage": RESULTS_PER_PAGE,
        "pageNumber": page
    }

    # Optional filter for year
    if year:
        payload["filters"] = [{"field": "publicationYear", "values": [str(year)]}]

    async with aiohttp.ClientSession() as session:
        data = await fetch_with_timeouts(session, search_url, payload, headers)
        if not data:
            return []

        papers = []
        for record in data.get("records", []):
            authors_list = [author.get("preferredName", "") for author in record.get("authors", [])]

            # Optional post-filtering by author
            if author and not any(author.lower() in a.lower() for a in authors_list):
                continue

            papers.append({
                "title": record.get("articleTitle", "No Title Available"),
                "authors": ", ".join(authors_list) if authors_list else "Unknown Author",
                "abstract": record.get("abstract", "No abstract available"),
                "year": record.get("publicationYear", "Unknown Year"),
                "url": f"https://ieeexplore.ieee.org{record.get('documentLink')}" if record.get('documentLink') else "#",
                "source": "IEEE Xplore",
                "publisher": record.get("publicationTitle", "Unknown Publisher")
            })

        return papers

MAX_RETRIES = 2
RETRY_BACKOFF = 2  # seconds

async def fetch_from_semantic_scholar(keywords,year,author, offset=0):
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={keywords}&offset={offset}&limit={RESULTS_PER_PAGE}"
        f"&fields=title,authors,abstract,year,url,venue"
    )

    timeout = aiohttp.ClientTimeout(total=5)

    for attempt in range(MAX_RETRIES):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        break
                    elif response.status == 429:
                        print(f"Rate limited. Retrying in {RETRY_BACKOFF ** attempt} seconds...")
                        await asyncio.sleep(RETRY_BACKOFF ** attempt)
                    else:
                        print(f"HTTP Error {response.status}")
                        return []
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(RETRY_BACKOFF ** attempt)
    else:
        print("Max retries exceeded.")
        return []

    papers = []
    for paper in data.get('data', []):
        authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
        papers.append({
            "title": paper.get("title", "No Title"),
            "authors": authors or "Unknown Authors",
            "abstract": paper.get("abstract", "No abstract available"),
            "url": paper.get("url", ""),
            "source": "Semantic Scholar",
            "year": paper.get("year", "Unknown Year"),
            "publisher": paper.get("venue", "Unknown Venue")
        })

    return papers

# Combined async fetcher
async def fetch_all_sources_parallel(keywords, year, author, offset):
    results = await asyncio.gather(
        fetch_from_ieee_xplore(keywords, year, author, offset),
        fetch_from_semantic_scholar(keywords, year, author, offset),
        fetch_from_doaj(keywords, year, author, offset),
        fetch_from_arxiv(keywords, year, author, offset),
        fetch_from_openalex(keywords, year, author, offset),
        fetch_from_crossref(keywords, year, author, offset),
        fetch_from_europepmc(keywords, year, author, offset),
        return_exceptions=True
    )
    papers = []
    for r in results:
        if isinstance(r, list):
            papers.extend(r)
    return papers

@app.route('/results/<int:page>')
def results(page):
    keywords = session.get('keywords', '')
    year = session.get('year', '')
    author = session.get('author', '')
    offset = page - 1

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    papers = loop.run_until_complete(fetch_all_sources_parallel(keywords, year, author, offset))

    session['papers'] = papers

    source_counter = Counter(p['source'] for p in papers)
    year_counter = Counter(str(p['year']) for p in papers if p['year'])

    return render_template('results.html', papers=papers, page=page,
                           source_labels=list(source_counter.keys()),
                           source_counts=list(source_counter.values()),
                           year_labels=sorted(year_counter.keys()),
                           year_counts=[year_counter[y] for y in sorted(year_counter.keys())])
@app.route('/download_csv')
def download_csv():
    papers = session.get('papers', [])
    if not papers:
        return "No papers to download", 400

    proxy = io.StringIO()
    fieldnames = ['title', 'authors', 'abstract', 'url', 'source', 'year']
    writer = csv.DictWriter(proxy, fieldnames=fieldnames)
    writer.writeheader()

    for paper in papers:
        # Safely get values and handle lists like authors
        writer.writerow({
            'title': paper.get('title', ''),
            'authors': ', '.join(paper.get('authors', [])) if isinstance(paper.get('authors'), list) else paper.get('authors', ''),
            'abstract': paper.get('abstract', ''),
            'url': paper.get('url', ''),
            'source': paper.get('source', ''),
            'year': paper.get('year', '')
        })

    mem = io.BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    proxy.close()
    return send_file(mem, as_attachment=True, download_name='papers.csv', mimetype='text/csv')


if __name__ == '__main__':
    app.run(debug=True)