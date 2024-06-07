import requests
import argparse
import concurrent.futures
import os
import signal
import sys

def fetch_url(url, search_string, timeout, waf_bypass_headers):
    try:
        response = requests.get(url, headers=waf_bypass_headers, timeout=timeout)
        if search_string in response.text:
            return url
    except requests.Timeout:
        print(f"Timeout ao acessar {url}")
    except requests.TooManyRedirects:
        print(f"Redirecionamentos excessivos ao acessar {url}")
    except requests.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
    return None

def scan_sites(file_with_sites, search_string, output_file, threads, timeout):
    try:
        with open(file_with_sites, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Erro: Arquivo {file_with_sites} não encontrado.")
        sys.exit(1)
    except IOError as e:
        print(f"Erro ao ler o arquivo {file_with_sites}: {e}")
        sys.exit(1)
    
    waf_bypass_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'X-Forwarded-For': '127.0.0.1',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    found_urls = []
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(fetch_url, url, search_string, timeout, waf_bypass_headers): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result:
                    found_urls.append(result)
    except Exception as e:
        print(f"Erro durante a execução das threads: {e}")
        sys.exit(1)
    
    try:
        with open(output_file, 'w') as f:
            for url in found_urls:
                f.write(f"{url}\n")
    except IOError as e:
        print(f"Erro ao escrever no arquivo {output_file}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Scanner de sites para buscar uma string específica.")
    parser.add_argument('-f', '--file', required=True, help='Arquivo com a lista de sites.')
    parser.add_argument('-s', '--search', required=True, help='String que estou buscando.')
    parser.add_argument('-o', '--output', required=True, help='Arquivo para salvar os sites encontrados.')
    parser.add_argument('-t', '--threads', type=int, default=5, help='Número de threads. Padrão: 5.')
    parser.add_argument('-u', '--timeout', type=int, default=5, help='Timeout de cada requisição em segundos. Padrão: 5.')
    parser.add_argument('-m', '--detach', action='store_true', help='Colocar o processo em segundo plano.')
    
    args = parser.parse_args()

    if args.detach:
        try:
            pid = os.fork()
            if pid > 0:
                print(f"Processo em segundo plano com PID {pid}.")
                os._exit(0)
        except OSError as e:
            print(f"Erro ao criar processo em segundo plano: {e}")
            sys.exit(1)
    
    try:
        scan_sites(args.file, args.search, args.output, args.threads, args.timeout)
    except KeyboardInterrupt:
        print("Processo interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
