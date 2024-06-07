import argparse
import re

def filtrar_links(input_file, output_file, variable_name, new_value):
    try:
        with open(input_file, 'r') as infile:
            lines = infile.readlines()
            print(f"Leu {len(lines)} linhas do arquivo '{input_file}'")

        with open(output_file, 'w') as outfile:
            for line in lines:
                # Usar expressão regular para substituir o valor da variável especificada
                modified_line = re.sub(rf"({re.escape(variable_name)}=)[^&]*", rf"\1{new_value}", line)
                outfile.write(modified_line)
                print(f"Original: {line.strip()} | Modificado: {modified_line.strip()}")

        print(f"Arquivo '{output_file}' foi criado com sucesso.")
    except FileNotFoundError:
        print(f"Erro: arquivo '{input_file}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Filtra e substitui valores de variáveis específicas em uma lista de links.')
    parser.add_argument('-f', '--file', type=str, required=True, help='Arquivo de entrada contendo os links.')
    parser.add_argument('-o', '--output', type=str, required=True, help='Arquivo de saída para salvar os links modificados.')
    parser.add_argument('-v', '--variable', type=str, required=True, help='Nome da variável cujo valor deve ser substituído.')
    parser.add_argument('-n', '--newvalue', type=str, required=True, help='Novo valor para substituir o valor da variável.')

    args = parser.parse_args()

    filtrar_links(args.file, args.output, args.variable, args.newvalue)
