import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import argparse
import threading
import random
import csv
import os
import signal
import pickle
from queue import Queue
import publicsuffix2

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, como Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    # Adicione mais User-Agents aqui conforme necessário
]

EXCLUDED_DOMAINS = [
    'github.com', 'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com'
    # Adicione mais domínios aqui conforme necessário
]

if os.path.exists('ignore.txt'):
    with open('ignore.txt', 'r') as file:
        excluded_domains_from_file = [line.strip() for line in file.readlines()]
        EXCLUDED_DOMAINS.extend(excluded_domains_from_file)

class WebCrawler:
    def __init__(self, base_urls, max_threads, output_file, timeout, capture_main_only, capture_base_domain_only):
        self.base_urls = base_urls
        self.visited_urls = set()
        self.queued_urls = set()
        self.queue = Queue()
        self.output_file = output_file
        self.lock = threading.Lock()
        self.timeout = timeout
        self.max_threads = max_threads
        self.capture_main_only = capture_main_only
        self.capture_base_domain_only = capture_base_domain_only
        self.state_file = 'crawler_state.pkl'
        self.success_count = 0
        self.error_count = 0

        # Load previous state if exists
        self.load_state()

        # Enqueue initial URLs
        for url in base_urls:
            self.queue.put(url)
            self.queued_urls.add(url)

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.graceful_shutdown)

        # Start threads
        for _ in range(max_threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()

    def fetch_page(self, url):
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            self.success_count += 1
            return response.text
        except requests.RequestException as e:
            self.error_count += 1
            return None

    def parse_links(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('javascript:') or href.startswith('#'):
                continue
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)
            domain = publicsuffix2.get_sld(parsed_url.netloc)
            if domain not in EXCLUDED_DOMAINS:
                if self.capture_base_domain_only:
                    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    links.add(base_domain)
                elif self.capture_main_only:
                    links.add(full_url)
                else:
                    links.add(full_url)
        return links

    def worker(self):
        while True:
            url = self.queue.get()
            if url not in self.visited_urls:
                html = self.fetch_page(url)
                if html:
                    with self.lock:
                        self.visited_urls.add(url)
                        with open(self.output_file, 'a', newline='', encoding='utf-8') as file:
                            writer = csv.writer(file)
                            writer.writerow([url])
                    links = self.parse_links(html, url)
                    for link in links:
                        if link not in self.visited_urls and link not in self.queued_urls:
                            self.queue.put(link)
                            self.queued_urls.add(link)
            self.queue.task_done()

    def save_state(self):
        with self.lock:
            state = {
                'visited_urls': self.visited_urls,
                'queued_urls': list(self.queue.queue),
            }
            with open(self.state_file, 'wb') as f:
                pickle.dump(state, f)
            print('State saved.')

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'rb') as f:
                state = pickle.load(f)
                self.visited_urls = state['visited_urls']
                for url in state['queued_urls']:
                    self.queue.put(url)
                    self.queued_urls.add(url)
            print('State loaded.')

    def graceful_shutdown(self, signum, frame):
        print('Graceful shutdown initiated...')
        self.save_state()
        exit(0)

    def start(self):
        self.queue.join()

def main():
    parser = argparse.ArgumentParser(description="A simple web crawler with threading and output")
    parser.add_argument('base_url', nargs='?', type=str, help='The base URL to start crawling from')
    parser.add_argument('--file', '-f', type=str, help='File with a list of URLs to start crawling from')
    parser.add_argument('--max_threads', '-m', type=int, default=5, help='Maximum number of threads to use')
    parser.add_argument('--output_file', '-o', type=str, default='output.csv', help='Output CSV file to save the results')
    parser.add_argument('--timeout', '-t', type=int, default=10, help='Timeout for HTTP requests in seconds')
    parser.add_argument('--capture_main_only', action='store_true', help='Capture only the main URL without following links')
    parser.add_argument('--capture_base_domain_only', action='store_true', help='Capture only the base domain without subdomains or paths')

    args = parser.parse_args()

    base_urls = []
    if args.file:
        if os.path.exists(args.file):
            with open(args.file, 'r') as file:
                base_urls = [line.strip() for line in file.readlines()]
        else:
            print(f"File {args.file} not found.")
            return
    elif args.base_url:
        base_urls = [args.base_url]
    else:
        print("Either a base URL or a file with URLs must be provided.")
        return

    # Write CSV header
    if not os.path.exists(args.output_file):
        with open(args.output_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['URL'])

    crawler = WebCrawler(base_urls, args.max_threads, args.output_file, args.timeout, args.capture_main_only, args.capture_base_domain_only)
    crawler.start()

if __name__ == "__main__":
    main()
