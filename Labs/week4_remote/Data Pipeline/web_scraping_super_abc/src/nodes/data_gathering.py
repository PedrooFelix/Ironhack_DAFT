import logging
from src.params import Params
import pandas as pd
import os
import concurrent.futures
import urllib.request
from bs4 import BeautifulSoup
import numpy as np
import re
import csv


logger = logging.getLogger('nodes.data_gathering')


def get_product_data(url,html):
    """
    Busca os dados de cada produto através de web scraping, e appenda em um arquivo csv
    @param url: link do produto
    """
    #faz o request na url e busca o html da página
    soup = BeautifulSoup(html, 'lxml')
    #busca as informações de categorias do produto
    #tenta buscar de duas formas a categoria
    categorias = soup.find_all('li', {'typeof': 'v:Breadcrumb'})
    if len(categorias) == 0:
        categorias = soup.find_all('li', {'itemprop': 'itemListElement'})
    #cria uma lista com categorias excluindo um item que não se refere a categoria
    categorias = [item.text for item in categorias if item.text != 'abcemcasa']
    # caso o scrap tenha sido efetuado corretamente salva a categoria, se não assume como NAN
    try:
        cat1 = categorias[0]
        cat2 = categorias[1]
        cat3 = categorias[2] if len(categorias) == 3 else np.nan
    except:
        cat1 = np.nan
        cat2 = np.nan
        cat3 = np.nan
    #busca a descrição para o produto
    descricao = soup.find('h1').text
    #busca o preço do produto, para produtos indisponiveis assume como NAN
    try:
        preco = soup.find('strong', {'class': 'skuBestPrice'}).text
        preco = float(preco.split(' ')[1].replace(',', '.'))
    except:
        preco = np.nan
    #busca link da imagem
    imagem = soup.find('div', {'id': 'image'}).find('a')['href']
    #através de duas formas usando regex busca o ean
    try:
        ean = re.findall(r'(\d+)', re.findall(r'/\d+\w', url)[0])[0]
    except:
        try:
            ean = re.findall(r'(\d+)', re.findall(r'/\d+.jpg', imagem)[0])[0]
        except:
            ean = np.nan
    #cria lista com todos os dados a serem salvos como uma row no csv
    return [url,ean,cat1,cat2,cat3,descricao,preco,imagem]

def update(params):
    f = open(params.product_links)
    urls = list(csv.reader(f))
    urls = [url[0] for url in urls]
    urls = [url.split('https://') for url in urls]
    URLS = ['https://' + site for url in urls for site in url if site != '']
    URLS = list(set(URLS))
    # Retrieve a single page and report the url and contents
    def load_url(url, timeout):
        with urllib.request.urlopen(url) as response:
            return response.read()

    dados = []
    # We can use a with statement to ensure threads are cleaned up promptly
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                dados.append(get_product_data(url, data))
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
                pass
            else:
                pass

    df = pd.DataFrame(data=dados, columns=['url','ean','cat1','cat2','cat3','desc','preco','imagem'])
    df.to_csv(Params.data_csv)


def done(params):
    files = os.listdir(Params.path_data_processed)
    file_to_find = Params.today + '.csv'
    if file_to_find in files:
        return True
    else:
        return False
