import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import concurrent.futures
import logging
from openpyxl import Workbook

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create an Excel workbook and sheet
workbook = Workbook()
sheet = workbook.active
sheet.title = "Downloaded PDFs"
sheet.append(["Website", "PDF Link", "PDF File Name"])

def get_all_links(url, base_url, visited):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # Set encoding to apparent encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(base_url, link['href']) for link in soup.find_all('a', href=True)]
        logging.info(f"Found {len(links)} links on {url}")
        return links
    except requests.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return []

def get_pdf_links(url, base_url, visited):
    pdf_links = []
    links_to_visit = [url]

    while links_to_visit:
        current_url = links_to_visit.pop()
        if current_url in visited:
            continue
        visited.add(current_url)

        links = get_all_links(current_url, base_url, visited)
        for link in links:
            if link.endswith('.pdf'):
                pdf_links.append(link)
            elif urlparse(link).netloc == urlparse(base_url).netloc and link not in visited:
                links_to_visit.append(link)

    logging.info(f"Found {len(pdf_links)} PDF links on {url}")
    return pdf_links

def download_pdf(pdf_link, download_folder, website):
    try:
        pdf_response = requests.get(pdf_link)
        pdf_response.raise_for_status()
        pdf_name = os.path.join(download_folder, os.path.basename(pdf_link))

        with open(pdf_name, 'wb') as pdf_file:
            pdf_file.write(pdf_response.content)
        logging.info(f'Downloaded: {pdf_name}')
        sheet.append([website, pdf_link, os.path.basename(pdf_name)])
    except requests.RequestException as e:
        logging.error(f"Error downloading {pdf_link}: {e}")

def download_pdfs(pdf_links, download_folder, website):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(download_pdf, pdf_link, download_folder, website) for pdf_link in pdf_links]
        concurrent.futures.wait(futures)

def process_website(url, download_folder):
    logging.info(f"Processing website: {url}")
    visited = set()
    pdf_links = get_pdf_links(url, url, visited)
    if pdf_links:
        download_pdfs(pdf_links, download_folder, url)
    else:
        logging.info(f"No PDF links found for {url}")

if __name__ == "__main__":
    # Read websites from the text file
    with open('websites.txt', 'r') as file:
        websites = [line.strip() for line in file.readlines()]

    download_folder = '/Users/Rajender_Singh_Negi/code/pdf/download'  # Replace with your desired path

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(process_website, url, download_folder) for url in websites]
        concurrent.futures.wait(futures)

    # Save the Excel workbook
    workbook.save("downloaded_pdfs.xlsx")

    logging.info("Processing completed.")
