import os
import shutil
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {str(e)}")
        return ""

# Diretório com os PDFs
pdf_directory = 'F:\PythonPDFReader\pdf_database'

# Palavras-chave relevantes para o tema
keywords = ['CFD', 'carbon capture', 'post combustion', 'adsorption', 'simulation', 'computational fluidodynamics', 'exhaution gases', 'modelling', 'CO2', 'adsorbents']

# Lista para armazenar os textos e nomes dos arquivos
texts = []
filenames = []

# Extrair texto de todos os PDFs
for filename in os.listdir(pdf_directory):
    if filename.endswith('.pdf'):
        file_path = os.path.join(pdf_directory, filename)
        text = extract_text_from_pdf(file_path)
        if text:  # Só adiciona se o texto foi extraído com sucesso
            texts.append(text)
            filenames.append(filename)

# Verificar se há textos para processar
if not texts:
    print("Nenhum texto foi extraído dos PDFs. Verifique os arquivos e permissões.")
    exit()

# Criar um vetor TF-IDF para as palavras-chave
vectorizer = TfidfVectorizer()
keyword_vector = vectorizer.fit_transform([' '.join(keywords)])

# Calcular a similaridade entre cada documento e as palavras-chave
similarities = []
for text in texts:
    doc_vector = vectorizer.transform([text])
    similarity = cosine_similarity(keyword_vector, doc_vector)[0][0]
    similarities.append(similarity)

# Criar um dicionário com os nomes dos arquivos e suas pontuações
scores = dict(zip(filenames, similarities))

# Ordenar os arquivos por pontuação (do maior para o menor)
sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

# Criar diretório para os artigos mais relevantes
output_directory = 'mais_relevantes'
os.makedirs(output_directory, exist_ok=True)

# Copiar os 50 artigos mais relevantes (ou menos, se houver menos de 50) para o novo diretório
for filename, score in sorted_scores[:min(50, len(sorted_scores))]:
    source_path = os.path.join(pdf_directory, filename)
    destination_path = os.path.join(output_directory, filename)
    shutil.copy2(source_path, destination_path)

print(f"Os {min(50, len(sorted_scores))} artigos mais relevantes foram copiados para a pasta 'mais_relevantes'.")