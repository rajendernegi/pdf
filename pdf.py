
# Import the modules
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import concurrent.futures
import logging
from openpyxl import Workbook
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create an Excel workbook and sheet
workbook = Workbook()
sheet = workbook.active
sheet.title = "Downloaded PDFs"
sheet.append(["Website", "PDF Link", "PDF File Name"])

def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[403, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def get_all_links(session, url, base_url, visited):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': base_url,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # Set encoding to apparent encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(base_url, link['href']) for link in soup.find_all('a', href=True)]
        logging.info(f"Found {len(links)} links on {url}")
        return links
    except requests.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return []

def get_pdf_links(session, url, base_url, visited):
    pdf_links = []
    links_to_visit = [url]

    while links_to_visit:
        current_url = links_to_visit.pop()
        if current_url in visited:
            continue
        visited.add(current_url)

        links = get_all_links(session, current_url, base_url, visited)
        for link in links:
            if link.endswith('.pdf'):
                pdf_links.append(link)
            elif urlparse(link).netloc == urlparse(base_url).netloc and link not in visited:
                links_to_visit.append(link)

        # Add a delay between requests to avoid being flagged as a bot
        time.sleep(1)

    logging.info(f"Found {len(pdf_links)} PDF links on {url}")
    return pdf_links

def download_pdf(session, pdf_link, download_folder, website):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': website,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'application/pdf'
    }
    try:
        pdf_response = session.get(pdf_link, headers=headers)
        pdf_response.raise_for_status()
        pdf_name = os.path.join(download_folder, os.path.basename(pdf_link))

        with open(pdf_name, 'wb') as pdf_file:
            pdf_file.write(pdf_response.content)
        logging.info(f'Downloaded: {pdf_name}')
        sheet.append([website, pdf_link, os.path.basename(pdf_name)])
    except requests.RequestException as e:
        logging.error(f"Error downloading {pdf_link}: {e}")

def download_pdfs(session, pdf_links, download_folder, website):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(download_pdf, session, pdf_link, download_folder, website) for pdf_link in pdf_links]
        concurrent.futures.wait(futures)

def process_website(url, download_folder):
    logging.info(f"Processing website: {url}")
    visited = set()
    session = create_session()
    pdf_links = get_pdf_links(session, url, url, visited)
    if pdf_links:
        download_pdfs(session, pdf_links, download_folder, url)
    else:
        logging.info(f"No PDF links found for {url}")

if __name__ == "__main__":
    # List of websites to process
    websites = [
        'https://investor.harley-davidson.com/overview/default.aspx',
        # Add more URLs here
    ]

    download_folder = 'pdf_download'  # Folder to save downloaded PDFs

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(process_website, url, download_folder) for url in websites]
        concurrent.futures.wait(futures)

    # Save the Excel workbook
    workbook.save("downloaded_pdfs.xlsx")

    logging.info("Processing completed.")
