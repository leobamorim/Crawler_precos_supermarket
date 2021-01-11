from datetime import date
import pandas as pd
import requests as req
from bs4 import BeautifulSoup
import sqlite3
from fpdf import FPDF, HTMLMixin

# Classe pra gerar PDF a partir de um HTML
class HTML2PDF(FPDF, HTMLMixin):
    pass


#função para pegar a data atual
def get_today_date():
    date_hj = date.today()
    return f'{date_hj.day}/{date_hj.month}/{date_hj.year}'


#Função para remover salto de linha no scraping
def remove_newlines(text):
    return text.replace('\n', '')


#Função de remoção de "lixo" que traz da web, retorna o tamanho da string
def remove_text(item):
    if 'R$' in item:
        #return item.index("R$")
        return item.index(" ")
    elif 'Unidade' in item:
        return item.index("Unidade")
    else:
        return len(item)


#Função que extrai o nome dos produtos da web e retorna um dataFrame com site e nome do produto
def extract_product_names(list_of_produts, site):
    itens_da_lista_de_produtos = list_of_produts.find_all('div', 'name-produto', recursive=True)
    df_name = pd.DataFrame(columns=['site', 'produto'])

    for name_produts in itens_da_lista_de_produtos:
        name_produts = name_produts.get_text()
        name_produts = remove_newlines(name_produts)
        index_unidade = remove_text(name_produts)
        name_produts = name_produts[:index_unidade]
        df_name = df_name.append({'site': site, 'produto': name_produts}, ignore_index=True)

    return df_name


#Função que extrai o preço da web e retorna um dataframe com preço e a data de aquisição dos dados
def extract_product_price(list_of_produts):
    price_list = list_of_produts.find_all('div', 'item-por')
    df_price = pd.DataFrame(columns=['valor', 'data'])
    date = get_today_date()

    for price in price_list:

        price_text = price.get_text()
        price_text = remove_newlines(price_text)
        price_text = price_text.strip()
        price_text = price_text.replace('R$', '')
        price_text = price_text.replace('Por', '').replace(':', '').replace(' ', '').replace(',','.')
        price_value = float(price_text)

        df_price = df_price.append({'valor': price_value, 'data': date}, ignore_index=True)

    return df_price

#Função para busca na web pelo "bloco" de info solicitada na .find e o retorna
def extract_product_list(URL):
    page = req.get(URL)
    soup = BeautifulSoup(page.text, 'html.parser')

    return soup.find(class_='box-produtos box-produtos--margin-top ec-itens')


#Função de conexão com o banco de Dados, se existir o banco, sobrescreve
def connect_db(data_db, df_supermarket):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)

    return df_supermarket.to_sql(data_db, connection, if_exists='replace')


#Função para inserir dados no banco de dados SQLITE
def insert(data_db, website, product, value):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    cursor.execute("SELECT MAX([index]) + 1 FROM supermarket")
    max_index = cursor.fetchone()
    max_index = max_index[0]

    cursor.execute("""
    INSERT INTO supermarket ([index], site, produto, valor, data)
    VALUES (?,?,?,?,?)
    """, (max_index, website, product, value, get_today_date()))

    connection.commit()

    connection.close()


#Função para encontrar um registro, baseado em um ID
def find_by_id(data_db, id):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    selection = f"SELECT * FROM supermarket  where [index] = {id}"
    cursor.execute(selection)

    return cursor.fetchone()


#Função para Deletar um registro do Banco de Dados
def delete(data_db,id):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM supermarket  WHERE [index] = ? """, (id,))

    connection.commit()

    connection.close()


#Função para fazer alterações de um registro no banco de Dados
def update(data_db, item):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    website = input('Digite o nome do site: ')
    product = input('Digite o nome do produto: ')
    value = input('Digite o valor: ')

    cursor.execute("""
    UPDATE supermarket SET site = ?, produto = ?, valor = ? WHERE [index] = ? """,
                   (website, product, value, item))
    connection.commit()

    connection.close()


#Função que cria uma tabela HTML e gera um relatório em PDF
def report(data_db):
    db_name = f'{data_db}.db'
    connection = sqlite3.connect(db_name)

    df = pd.read_sql_query("SELECT * FROM supermarket", connection)

    # Pegando as estatistica e atibuindo a eles um valor array - values
    df_summary = df.describe()
    values = df_summary.get('valor').values


    # DataFrame df, localizando o ID com o maior valor e menor valor,
    product_max_value = df.loc[df['valor'].idxmax()]
    product_min_value = df.loc[df['valor'].idxmin()]

    # Obtendo as estatisticas
    total = values[0]
    media = ("%.2f" % values[1])
    dp = ("%.2f" % values[2])
    min = values[3]
    p25 = values[4]
    p50 = values[5]
    p75 = values[6]
    max = values[7]


    # Criando tabela HTML para o Relatório
    table = f"""
        <h1 align="center">Relatório de Dados</h1>
        
        <table border="0" align="center" width="100%">
            <thead>
                <tr>
                    <th width="10%">Qtd</th>
                    <th width="10%">Media</th>
                    <th width="10%">DP</th>
                    <th width="10%">Min</th>
                    <th width="10%">P25</th>
                    <th width="10%">P50</th>
                    <th width="10%">P75</th>
                    <th width="10%">Max</th>
                </tr>
            </thead>
            
            <tbody>
                <tr>
                    <td>{total}</td>
                    <td>{media}</td>
                    <td>{dp}</td>
                    <td>{min}</td>
                    <td>{p25}</td>
                    <td>{p50}</td>
                    <td>{p75}</td>
                    <td>{max}</td>
                </tr>
            </tbody>
        </table>
        <br>
        <h1> Informações  </h1>
        <h2> Estabelecimento - Maiores valores </h2>
        <p> Maior valor eh do estabelecimento: {product_max_value[1]} </p>
        <p> Com o produto: {product_max_value[2]} </p>
        <p> Com o preco: {product_max_value[3]}  </p>
        <br>
        <h2> Estabelecimento - Menores valores </h2>
        <p> Menor valor eh do estabelecimento: {product_min_value[1]} </p>
        <p> Com o produto: {product_min_value[2]} </p>
        <p> Com o preco: {product_min_value[3]}  </p>
        <br>
        
    """

    # Gerando o arquivo PDF
    pdf = HTML2PDF()
    pdf.add_page()
    pdf.write_html(table)
    pdf.output('relatorio.pdf')


#Função para extrair dados da página WEB
def extract_data_information(URL, site):
    data_extrabom = pd.DataFrame()
    NUM_PAGES = 9
    for i in range(1, NUM_PAGES):
        url_ = f'{URL}{i}'
        list_of_produts = extract_product_list(url_)

        df_name = extract_product_names(list_of_produts, site)
        df_price = extract_product_price(list_of_produts)

        df_temp = pd.concat([df_name, df_price], axis=1)
        data_extrabom = data_extrabom.append(df_temp, ignore_index=True)

    return data_extrabom


#Função que realiza o Scraping da web
def scraping():

    extrabom_url = 'https://www.extrabom.com.br/c/hortifruti/1/?page='
    extraplus_url = 'https://www.extraplus.com.br/c/hortifruti/1/?page='

    extrabom_df = extract_data_information(extrabom_url, 'Extrabom')
    extraplus_df = extract_data_information(extraplus_url, 'Extraplus')

    all_data = extrabom_df.append(extraplus_df, ignore_index=True)

    connect_db("supermarket", all_data)

    return all_data


#Função MENU de opções para escolha do usuário
def show_options():
    print('Opcoes:')
    print('1 - Inserir registro')
    print('2 - Apagar registro')
    print('3 - Editar registro')
    print('4 - Gerar relatorio PDF')
    print('5 - Sair')


#Função para executar a escolha do usuário
def do_action(option):
    if option == 1:
        website = input('Digite o nome do site: ')
        product = input('Digite o nome do produto: ')
        value = input('Digite o valor: ')
        insert("supermarket", website, product, value)

    elif option == 2:
        id = int(input('Insira o ID do item que voce deseja DELETAR: '))
        item = find_by_id("supermarket", id)
        print(item)

        yesorno = input('Você realmente deseja DELETAR o item, y/n ?:')
        if yesorno == 'y':
            delete("supermarket",id)
            print('Item deletado com sucesso!!!')


    elif option == 3:
        id = int(input('Insira o ID do item que voce deseja editar: '))
        item = find_by_id("supermarket", id)
        print(item)

        update("supermarket", id)

    elif option == 4:
        print('gerar relatorio')

        report("supermarket")

#MAIN
if __name__ == '__main__':
    print('Realizando scraping ...')
    scraping()
    while True:
        show_options()
        option = int(input('Digite o numero da opcao desejada: '))
        print(option)
        if option == 5:
            break
        do_action(option)

    print('Você saiu do sistema!')