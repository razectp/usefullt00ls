import requests
from bs4 import BeautifulSoup
import threading
import argparse
from tqdm import tqdm
import time
from urllib.parse import urljoin, urlparse

# Função para configurar o cabeçalho HTTP
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

# Função para extrair links de um site
def extract_links(url, timeout, headers, base_url):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Levanta exceção para status codes 4xx/5xx
        soup = BeautifulSoup(response.content, 'html.parser')
        links = [link.get('href') for link in soup.find_all('a')]
        cleaned_links = []
        for link in links:
            if link:
                absolute_url = urljoin(base_url, link)
                cleaned_links.append(absolute_url)
        return cleaned_links
    except Exception as e:
        print(f"Erro ao processar {url}: {e}")
        return []

# Função para processar cada site
def process_site(url, timeout, headers, output_file, progress_bar):
    base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
    links = extract_links(url, timeout, headers, base_url)
    with threading.Lock():
        with open(output_file, 'a') as file:
            for link in links:
                file.write(link + '\n')
    progress_bar.update(1)

# Função principal
def main(input_file, output_file, num_threads, timeout):
    # Lendo a lista de sites
    with open(input_file, 'r') as file:
        sites = [line.strip() for line in file.readlines()]

    headers = get_headers()
    progress_bar = tqdm(total=len(sites))

    threads = []
    for url in sites:
        while threading.active_count() > num_threads:
            time.sleep(0.1)
        thread = threading.Thread(target=process_site, args=(url, timeout, headers, output_file, progress_bar))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    progress_bar.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrator de links com threads")
    parser.add_argument("-f", "--file", required=True, help="Arquivo com a lista de sites")
    parser.add_argument("-o", "--output", required=True, help="Arquivo de saída para os links capturados")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Número de threads")
    parser.add_argument("-m", "--timeout", type=int, default=5, help="Timeout de cada requisição (em segundos)")

    args = parser.parse_args()

    # Limpando o arquivo de saída antes de começar
    open(args.output, 'w').close()

    main(args.file, args.output, args.threads, args.timeout)
