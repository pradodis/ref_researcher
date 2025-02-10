import redis
import requests
import json
import time

config_dict = {
    'overwrite_doi': {True: 'SOBRESCREVER a entrada.',
                       False: 'IGNORAR a nova entrada.' 
    }
}

def recuperar_nome_journal(issn):
    url = f"https://api.crossref.org/journals/{issn}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Levanta um erro se a resposta for um código de erro HTTP

        # Parsear o JSON da resposta
        journal_data = response.json()

        # Recuperar o nome do periódico
        nome_journal = journal_data['message']['title']
        return nome_journal
    except requests.HTTPError as http_err:
        print(f"Erro HTTP ocorreu: {http_err}")
        return "Not available"
    except requests.RequestException as err:
        print(f"Um erro ocorreu ao fazer a solicitação: {err}")
        return "Not available"
    except KeyError:
        print("Não foi possível encontrar o nome do periódico com o ISSN fornecido.")
        return "Not available"
    except IndexError:
        print("Não foi possível processar a informação de nome do periódico.")
        return "Not available"

def buscar_citacoes(doi):
    url = f"https://opencitations.net/index/coci/api/v1/citations/{doi}"
    try:
        response = requests.get(url)

        if response.status_code != 200:
            print("---> DOI FROM CITER NOT FOUND  <---")

        data = response.json()
        citacoes = [citacao["citing"] for citacao in data]

        return citacoes
    except requests.HTTPError as http_err:
        print(f"Erro HTTP ocorreu: {http_err}")
        return "Not available"
    except requests.RequestException as err:
        print(f"Um erro ocorreu ao fazer a solicitação: {err}")
        return "Not available"
    except KeyError:
        print("Não foi possível encontrar o nome do periódico com o ISSN fornecido.")
        return "Not available"
    except IndexError:
        print("Não foi possível processar a informação de nome do periódico.")
        return "Not available"
    
def buscar_dados_artigo(doi, esta_escaneado):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        if response.status_code != 200:
            print("---> !!! DOI " + str(doi) + " NOT FOUND. SEARCH THIS ENTRY MANUALLY.")
            return {
                "titulo": 'Not available',
                "autores": 'Not available',
                "abstract": 'Not available',
                "keywords": 'Not available',
                "revista": 'Not available',
                "data_publicacao": 'Not available',
                "weblink": 'Not available',
                "referencias": 'Not available',
                "issn": 'Not available',
                "publisher": 'Not available',
                "cited_by": 'Not available',
                "scanned": False
            }
        else:
            try:
                dados = response.json()
                isScanned  = esta_escaneado
                autores = dados['message']['author']
                lista_autores = []
                for autor in autores:
                    nome_autor = f"{autor['given']} {autor['family']}"
                    if 'affiliation' in autor:
                        filiacao_autor = autor['affiliation']#[0]['name']
                    else:
                        filiacao_autor = 'Not available'
                    lista_autores.append((nome_autor, filiacao_autor))

                titulo = dados['message'].get('title', 'Not available')[0]
                abstract = dados['message'].get('abstract', 'Not available')
                keywords = dados['message'].get('subject', 'Not available')  # CrossRef usa 'subject' para keywords
                revista = dados["container-title"][0] if "container-title" in dados else "Not available"
                data_publicacao = str(dados['message']['created']['date-parts'][0][0]) if "message" in dados else "Not available"
                weblink = dados['message'].get('URL', 'Not available')
                referencias_full = dados['message'].get('reference', {})
                referencias = []
                for ref in referencias_full:
                    try: 
                        referencias.append(ref.get('DOI', 'Not available'))
                    except:
                        print("---> " + str(ref) + " NOT FOUND, SEARCH FOR IT MANUALLY.")
                issn = dados['message'].get('ISSN', 'Not available')[0]
                if revista == "Not available" and issn != "N":
                    if not issn in issn_database:
                        revista = recuperar_nome_journal(issn)
                        issn_database[str(issn)] = revista
                    else:
                        revista = issn_database[str(issn)]

                publisher = dados['message'].get('publisher', 'Not available')
                cited_by = buscar_citacoes(doi)
                time.sleep(0.5)

                return {
                    "titulo": titulo,
                    "autores": lista_autores,
                    "abstract": abstract,
                    "keywords": keywords,
                    "revista": revista,
                    "data_publicacao": data_publicacao,
                    "weblink": weblink,
                    "referencias": referencias,
                    "issn": issn,
                    "publisher": publisher,
                    "cited_by": cited_by,
                    "scanned": isScanned
                }
            except:
                return {
                "titulo": 'Not available',
                "autores": 'Not available',
                "abstract": 'Not available',
                "keywords": 'Not available',
                "revista": 'Not available',
                "data_publicacao": 'Not available',
                "weblink": 'Not available',
                "referencias": 'Not available',
                "issn": 'Not available',
                "publisher": 'Not available',
                "cited_by": 'Not available',
                "scanned": False
            }
    except:
        return {
            "titulo": 'Not available',
            "autores": 'Not available',
            "abstract": 'Not available',
            "keywords": 'Not available',
            "revista": 'Not available',
            "data_publicacao": 'Not available',
            "weblink": 'Not available',
            "referencias": 'Not available',
            "issn": 'Not available',
            "publisher": 'Not available',
            "cited_by": 'Not available',
            "scanned": False
        }

def save_json_file(dicionario, diretorio):
    # Converter o dicionário para uma string JSON
    json_string = json.dumps(dicionario)

    # Escrever a string JSON em um arquivo
    with open(diretorio, 'w') as arquivo:
        arquivo.write(json_string)

def save_json_file_redis_doi(json_database_dir):
    if use_redis:
        pipeline = r.pipeline()
        for key, value in doi_database.items():
            value_json = json.dumps(value) if not isinstance(value, str) else value
            redis_key = f"dois:{key}"
            if isinstance(value, dict):
                for field, field_value in value.items():
                    pipeline.hset(redis_key, field, json.dumps(field_value))
            else:
                pipeline.hset(redis_key, "data", value_json)
        pipeline.execute()

    else:
        doi_database_json = json.dumps(doi_database)
        save_json_file(doi_database_json, json_database_dir)
    print('---> Dados DOI Salvos na Database ---')

def save_json_file_redis_issn(issn_database_json):
    if use_redis:
        pipeline = r.pipeline()
        for key, value in issn_database.items():
            value_json = json.dumps(value) if not isinstance(value, str) else value
            redis_key = f"issn:{key}"
            if isinstance(value, dict):
                for field, field_value in value.items():
                    pipeline.hset(redis_key, field, json.dumps(field_value))
            else:
                pipeline.hset(redis_key, "nome", value_json)
        pipeline.execute()

    else:
        issn_database_json = json.dumps(issn_database)
        save_json_file(issn_database_json, json_database_dir)
    print('---> Dados ISSN Salvos na Database ---')

def busca_relacionada(dados):
    print("---> RELATED SEARCH ACTIVATED ---> FETCHING DATA FOR REFERENCES AND CITATIONS")
    related_dois = dados["referencias"] + dados["cited_by"] 
    new_related_dois = []
    for key in related_dois:
        if (key in doi_database) or key == "Not available": 
            print(key + " <----> Already in database")
        else:
            new_related_dois.append(key)
            print(key + " <----> Key added for research")
    print("\n---> " + str(len(new_related_dois)) + " NEW ENTRIES FOUND.")
    dados_ref_lista = {}
    ref_number = 0
    for key in new_related_dois:
        ref_number = ref_number + 1
        print("---> FETCHING " + str(ref_number) + " OF " + str(len(new_related_dois)) + ": " + str(key))
        dados_ref = buscar_dados_artigo(key, False) #Busca dados do artigo
        dados_ref_lista[key] = dados_ref
    return dados_ref_lista

def buscar_dados_doi(doi, busca_relacionados, esta_escaneado):
    if (not doi in doi_database or doi_database[doi] is None):
        print("\n---> Importando dados da nuvem para DOI: " + str(doi))
        dados = buscar_dados_artigo(doi, esta_escaneado) #Busca dados do artigo
        for keys in dados['referencias'] + dados["cited_by"]:
            print(keys)
        print(f'\n---> CITES: {len(dados["referencias"])} \n---> CITED BY: {len(dados["cited_by"])}')
        if busca_relacionados: 
            ref_data = busca_relacionada(dados)
            for ref in ref_data: doi_database[ref] = ref_data[ref]
        doi_database[doi] = dados
        save_json_file_redis_doi(doi_database)
        save_json_file_redis_issn(issn_database)
    else:
        print("\n---> O DOI (" + str(doi) + ") ja possui informacoes salvas.\n---> A rotina esta configurada para " + config_dict['overwrite_doi'][overwrite_article])
        if overwrite_article:
            print("\n---> Importando dados da nuvem para DOI: " + str(doi))
            dados = buscar_dados_artigo(doi, esta_escaneado) #Busca dados do artigo
            for keys in dados['referencias'] + dados['cited_by']:
                print(keys)
            print(f'\n---> CITES: {len(dados["referencias"])} \n---> CITED BY: {len(dados["cited_by"])}')       
            if busca_relacionados: 
                ref_data = busca_relacionada(dados)
                for ref in ref_data: doi_database[ref] = ref_data[ref]
            doi_database[doi] = dados
            save_json_file_redis_doi(doi_database)
            save_json_file_redis_issn(issn_database)
    return dados
## MAIN
## PARAMETERS
overwrite_article = True
overwrite_related_search = True
use_redis = True
active_relactive_search = False
relactive_deep = 1
## END OF PARAMETERS

website_prefix = 'https://doi.org/'
arquivo_dois = 'Relevant_dois.txt'
dois = []
with open(arquivo_dois, 'r') as file:
    dois = file.read().splitlines()

vault = 'F:\pythonTestVault\pythonTest' # Path for vault
json_database_dir = 'C:\Windows\System32' # Path for saving JSON database

doi_database = {}
issn_database = {}
if use_redis: 
    r = redis.Redis(host='localhost', port=6379, db=0)
    # Verificando banco de dados
    cursor = '0' 
    result_dois = {}
    while cursor != 0:
        cursor, keys = r.scan(cursor=cursor, match='dois:*')
        for key in keys:
            key_type = r.type(key).decode('utf-8')
            if key_type == 'hash':
                result_dois = r.hgetall(key)
                # Decodificando os dados do hash
                decoded_result_dois = {k.decode('utf-8'): json.loads(v) for k, v in result_dois.items()}
                doi_database[key.decode('utf-8')[5::]] = decoded_result_dois
            else:
                print(f"Chave {key.decode('utf-8')} ignorada. Tipo: {key_type}")

    # Verificando se o resultado foi encontrado
    if result_dois is None:
        # Se não foi encontrado, retorna um dicionário vazio
        print("---> EMPTY DATABASE FOUND. CREATING A NEW ONE.")
        doi_database = {}
    else:
        # Se foi encontrado, retorna seus valores
        print("---> DATABASE RETRIEVED. KNOWN ENTRIES: " + str(len(doi_database)))
        print("-------------------------- DATABASE ------------------------")
        for keys in doi_database:
            print(keys)
        print("------------------------------------------------------------")
    
    cursor = '0'
    issn_database = {}

    while cursor != 0:
        cursor, keys = r.scan(cursor=cursor, match='issn:*')
        for key in keys:
            key_type = r.type(key).decode('utf-8')
            if key_type == 'hash':
                result_issn = r.hgetall(key)
                # Decodificando os dados do hash
                decoded_result_issn = {k.decode('utf-8'): v.decode('utf-8') for k, v in result_issn.items()}
                issn_database[key.decode('utf-8')[5:]] = decoded_result_issn
            else:
                print(f"Chave {key.decode('utf-8')} ignorada. Tipo: {key_type}")

    if not issn_database:
        # Se não foi encontrado, retorna um dicionário vazio
        print("---> EMPTY ISSN DATABASE FOUND. CREATING A NEW ONE.")
        issn_database = {}
    else:
        # Se foi encontrado, retorna seus valores
        print("---> ISSN DATABASE RETRIEVED. KNOWN ENTRIES: " + str(len(issn_database)))
        print("--------------------- ISSN DATABASE ------------------------")
        for key in issn_database:
            print(key)
        print("------------------------------------------------------------")

for doi in dois:
    dados_recuperados = buscar_dados_doi(doi, True, True)
    if active_relactive_search:
        for key in dados_recuperados['referencias'] + dados_recuperados["cited_by"]:
            if key != "Not available" and len(key) > 1:
                buscar_dados_doi(key, True, False)