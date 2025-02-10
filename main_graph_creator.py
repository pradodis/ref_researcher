from unidecode import unidecode
import json
import redis
import csv
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def preprocess_text(text):
    # Tokenização e remoção de stopwords
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(text.lower())
    return ' '.join([w for w in word_tokens if w.isalnum() and w not in stop_words])

def calculate_relevance(titles, keywords):
    processed_titles = [preprocess_text(title) for title in titles]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed_titles + [' '.join(keywords)])

    # Cálculo da similaridade
    cosine_similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1]).flatten()
    
    # Normalização dos resultados para o intervalo [0, 1]
    normalized_similarities = (cosine_similarities - np.min(cosine_similarities)) / (np.max(cosine_similarities) - np.min(cosine_similarities))
    
    return normalized_similarities.tolist()

def converter_caracteres(s):
    return unidecode(s)

def is_valid(s):
    # Define os caracteres que não devem estar na string
    not_allowed_chars = "NOT AVAILABLE"
    
    # Verifica se a string é exatamente "Not available"
    if s == "Not available":
        return False
    
    # Verifica se algum caractere da string está em not_allowed_chars
    if s in not_allowed_chars:
        return False
    
    # Se nenhum dos casos acima for verdadeiro, retorna False
    return True

def sanitize_string(text, no_spaces, capitals):
    # Converte todas as letras para maiúsculas
    if capitals: text = text.upper()
    # Remove os espaços
    if no_spaces: text = text.replace(" ", "")
    # Remove caracteres inválidos para nomes de arquivo no Windows
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    return text

# MAIN
# PARAMETERS
use_redis = True
keywords = ["CFD", "Computational", "CO2", "Carbon Capture", "Simulation", "Numerical", "Numeric", "Optimization", "Modelling", "Model", "BECCS", "Adsorption", "TSA", "Post Combustion"]
score_threshold =  0.4

# END OF PARAMETERS

website_prefix = 'https://doi.org/'
vault = 'F:\pythonTestVault\pythonTest' # Path for vault
json_database_dir = 'C:\Windows\System32' # Path for saving JSON database

doi_database = {}
if use_redis: 
    r = redis.Redis(host='localhost', port=6379, db=0)
    # Usando SCAN para iterar sobre todas as chaves que começam com 'dois:'
    cursor = '0'
    doi_database = {}
    
    while cursor != 0:
        cursor, keys = r.scan(cursor=cursor, match='dois:*')
        for key in keys:
            key_type = r.type(key).decode('utf-8')
            if key_type == 'hash':
                hash_data = r.hgetall(key)
                # Decodificando os dados do hash
                decoded_hash_data = {k.decode('utf-8'): json.loads(v) for k, v in hash_data.items()}
                doi_database[key.decode('utf-8')] = decoded_hash_data
            else:
                print(f"Chave {key.decode('utf-8')} ignorada. Tipo: {key_type}")
    
    if not doi_database:
        print("---> EMPTY DATABASE FOUND. CREATING A NEW ONE.")
    else:
        print("---> DATABASE RETRIEVED. KNOWN ENTRIES: " + str(len(doi_database)))
        print("-------------------------- DATABASE ------------------------")
        for key, value in doi_database.items():
            print(f"{key[5::]}: {value['titulo']}")
        print("------------------------------------------------------------")

# Avaliando Relevância
title_list = []
title_doi = {}
relevant_dois = []
for entry in doi_database:
    clean_title = sanitize_string(doi_database[entry]['titulo'], False, False)
    title_list.append(clean_title)
    title_doi[clean_title] = str(entry[5::])
relevance_scores = calculate_relevance(title_list, keywords)
relevance_dict = {}
for title, score in zip(title_list, relevance_scores):
    relevance_dict[title] = score
for tit, scr in relevance_dict.items():
    if scr >= score_threshold:
        relevant_dois.append(title_doi[tit])

# GERANDO NOS
nos = []
link_list = {}
index = 1
for entry in doi_database:
    try:
        clean_title = sanitize_string(doi_database[entry]['titulo'], False, False)
        nos.append({'Id': index, 'Label': clean_title, 'Type': 'Article', 'date': doi_database[entry]['data_publicacao'], 'scanned': int(doi_database[entry]['scanned']), "relevance": relevance_dict[clean_title], "doi": entry[5::]})
        link_list[entry[5::]] = index
        index = index + 1
        #for autor in doi_database[entry]['autores']:
        #    clean_author = sanitize_string(autor[0], True, True)
        #    if not clean_author in link_list and is_valid(clean_author):
        #        nos.append({'Id': index, 'Label': clean_author, 'Type': 'Author'})
        #        link_list[clean_author] = index
        #        index = index + 1
        #if doi_database[entry]['revista'] != 'Not available':
        #    clean_revista = sanitize_string(doi_database[entry]['revista'], False, False)
        #    if not clean_revista in link_list and is_valid(clean_revista):
        #        nos.append({'Id': index, 'Label': clean_revista, 'Type': 'Journal'})
        #        link_list[clean_revista] = index
        #        index = index + 1
        #for keyword in doi_database[entry]['keywords'] :
        #    clean_key = sanitize_string(keyword, True, True)
        #    if not clean_key in link_list and is_valid(clean_key):
        #        nos.append({'Id': index, 'Label': clean_key, 'Type': 'Keyword'})
        #        link_list[clean_key] = index
        #        index = index + 1
    except:
        print('Trabalho sem titulo')

# GERANDO ARESTAS
arestas = []
index = 1
for entry in doi_database:
    if entry[5::] in link_list:
        for link in doi_database[entry]["referencias"]:
            if link in link_list: 
                vector_insert = {'Source': link_list[entry[5::]], 'Target': link_list[link], 'Type': 'Directed', 'Id': 'A'+str(index), 'Weight': 1.0, 'cat': 'Citation'}
                if not vector_insert in arestas: 
                    arestas.append(vector_insert)
                    index = index + 1
        #for autor in doi_database[entry]['autores']:
        #    clean_author = sanitize_string(autor[0], True, True)
        #    if clean_author in link_list: 
        #        arestas.append({'Source': link_list[entry], 'Target': link_list[clean_author], 'Type': 'Directed', 'Id': 'A'+str(index), 'Weight': 1.0, 'cat': 'Authorship'})
        #        index = index + 1
        #clean_revista = sanitize_string(doi_database[entry]['revista'], False, False)
        #if clean_revista in link_list:
        #    arestas.append({'Source': link_list[entry], 'Target': link_list[clean_revista], 'Type': 'Directed', 'Id': 'A'+str(index), 'Weight': 1.0, 'cat': 'Journal'})
        #index = index + 1
        #for keyword in doi_database[entry]['keywords']:
        #    clean_key = sanitize_string(keyword, True, True)
        #    if clean_key in link_list:
        #        arestas.append({'Source': link_list[entry], 'Target': link_list[clean_key], 'Type': 'Directed', 'Id': 'A'+str(index), 'Weight': 1.0, 'cat': 'Keyword'})
        #        index = index + 1

# Escrever DOIs falhos em um arquivo
with open("Relevant_dois.txt", "w") as f:
    for doi in relevant_dois:
        f.write(doi +"\n")

# Removing Double Links
print("---> REMOVING DOUBLES")
relation_list = []
remove_list = []
for entry in arestas:
    if not [entry["Source"], entry["Target"]] in relation_list:
        relation_list.append([entry["Source"], entry["Target"]])
    else:
        remove_list.append(entry)
for entry in remove_list:
    arestas.remove(entry)

# Escrever o arquivo de nós
with open('nodes.csv', 'w', newline='', encoding='utf-8') as nodes_file:
    fieldnames = ['Id', 'Label', 'Type', "date", "scanned","relevance","doi"]
    writer = csv.DictWriter(nodes_file, fieldnames=fieldnames)

    writer.writeheader()
    for no in nos:
        writer.writerow(no)

# Escrever o arquivo de arestas
with open('edges.csv', 'w', newline='', encoding='utf-8') as edges_file:
    fieldnames = ['Source', 'Target', 'Type', 'Id', 'Weight', 'Label', 'cat']
    writer = csv.DictWriter(edges_file, fieldnames=fieldnames)

    writer.writeheader()
    for aresta in arestas:
        writer.writerow(aresta)

print("Arquivos 'nodes.csv' e 'edges.csv' criados com sucesso.")