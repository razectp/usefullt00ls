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
    def __init__(self, base_url, max_threads, output_file, timeout, capture_main_only, capture_base_domain_only):
        self.base_url = base_url
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

        # Load previous state if exists
        self.load_state()

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.graceful_shutdown)

        # Start threads
        for _ in range(max_threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()

    def fetch_page(self, url):
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException:
            return None

    def extract_links(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            full_link = urljoin(base_url, link)
            if full_link.startswith('http') and not self.is_invalid_domain(full_link):
                links.add(full_link)
        return links

    def is_invalid_domain(self, url):
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        for excluded_domain in EXCLUDED_DOMAINS:
            if domain.endswith(excluded_domain):
                return True

        domain_suffix = publicsuffix2.get_sld(domain)
        if domain_suffix is None:
            return True
        
        return False

    def get_base_domain(self, url):
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        return publicsuffix2.get_sld(domain)

    def crawl(self, url):
        if url in self.visited_urls:
            return
        with self.lock:
            self.visited_urls.add(url)
        
        print(f'Crawling: {url}')
        
        page_content = self.fetch_page(url)
        if page_content:
            with self.lock:
                self.write_output(url)
            if not self.capture_main_only:
                links = self.extract_links(page_content, url)
                for link in links:
                    if link not in self.visited_urls and link not in self.queued_urls:
                        if self.capture_base_domain_only:
                            base_domain = self.get_base_domain(link)
                            full_base_domain_url = f"https://{base_domain}"
                            if full_base_domain_url not in self.visited_urls and full_base_domain_url not in self.queued_urls:
                                self.queue.put(full_base_domain_url)
                                self.queued_urls.add(full_base_domain_url)
                        else:
                            self.queue.put(link)
                            self.queued_urls.add(link)

    def worker(self):
        while True:
            url = self.queue.get()
            self.crawl(url)
            self.queue.task_done()

    def start(self):
        if not self.queue.qsize():
            self.queue.put(self.base_url)
            self.queued_urls.add(self.base_url)
        self.queue.join()

    def write_output(self, url):
        with open(self.output_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([url])

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

def main():
    parser = argparse.ArgumentParser(description="A simple web crawler with threading and output")
    parser.add_argument('base_url', type=str, help='The base URL to start crawling from')
    parser.add_argument('--max_threads', type=int, default=5, help='Maximum number of threads to use')
    parser.add_argument('--output_file', type=str, default='output.csv', help='Output CSV file to save the results')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for HTTP requests in seconds')
    parser.add_argument('--capture_main_only', action='store_true', help='Capture only the main URL without following links')
    parser.add_argument('--capture_base_domain_only', action='store_true', help='Capture only the base domain without subdomains or paths')
    
    args = parser.parse_args()

    # Write CSV header
    if not os.path.exists(args.output_file):
        with open(args.output_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['URL'])

    crawler = WebCrawler(args.base_url, args.max_threads, args.output_file, args.timeout, args.capture_main_only, args.capture_base_domain_only)
    crawler.start()

if __name__ == "__main__":
    main()
