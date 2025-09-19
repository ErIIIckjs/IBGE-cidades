from flask import Flask, render_template, request, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import json
import csv
import os

app = Flask(__name__)

# Arquivo para armazenar o histórico de consultas
HISTORICO_FILE = 'historico_consultas.json'

class IBGEScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def acessar_link(self, url):
        """Acessa o link fixo da cidade"""
        try:
            print(f"🌐 Acessando: {url}")
            self.driver.get(url)
            time.sleep(5)  # Aumentei o tempo para garantir carregamento
            return True
        except Exception as e:
            print(f"❌ Erro ao acessar {url}: {e}")
            return False

    def extrair_dados_simples(self):
        """Extrai informações básicas da página"""
        dados = {
            'localidade': '',
            'populacao': '',
            'ano_censo': '',
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Localidade - usando By.ID como solicitado
            try:
                elemento = self.driver.find_element(By.ID, "localidade")
                dados['localidade'] = elemento.text.strip()
            except Exception as e:
                print(f"❌ Erro ao encontrar localidade por ID: {e}")
                # Fallback: tentar por classe caso o ID não funcione
                try:
                    elemento = self.driver.find_element(By.CLASS_NAME, "localidade")
                    dados['localidade'] = elemento.text.strip()
                except:
                    pass

            # População
            try:
                elemento = self.driver.find_element(By.CLASS_NAME, "indicador__valor")
                dados['populacao'] = elemento.text.strip()
            except:
                pass

            # Ano do Censo
            try:
                elemento = self.driver.find_element(By.CLASS_NAME, "indicador__periodo")
                dados['ano_censo'] = elemento.text.strip()
            except:
                pass

            return dados

        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return dados

    def fechar(self):
        self.driver.quit()

# URLs fixas das 5 cidades
CIDADES = {
    "sao_paulo": {
        "url": "https://cidades.ibge.gov.br/brasil/sp/sao-paulo/panorama",
        "nome": "São Paulo"
    },
    "belo_horizonte": {
        "url": "https://cidades.ibge.gov.br/brasil/mg/belo-horizonte/panorama",
        "nome": "Belo Horizonte"
    },
    "rio_de_janeiro": {
        "url": "https://cidades.ibge.gov.br/brasil/rj/rio-de-janeiro/panorama",
        "nome": "Rio de Janeiro"
    },
    "salvador": {
        "url": "https://cidades.ibge.gov.br/brasil/ba/salvador/panorama",
        "nome": "Salvador"
    },
    "fortaleza": {
        "url": "https://cidades.ibge.gov.br/brasil/ce/fortaleza/panorama",
        "nome": "Fortaleza"
    }
}

def carregar_historico():
    """Carrega o histórico de consultas do arquivo"""
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_historico(historico):
    """Salva o histórico de consultas no arquivo"""
    with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

def adicionar_ao_historico(dados):
    """Adiciona uma nova consulta ao histórico"""
    historico = carregar_historico()
    
    # Adiciona a nova consulta no início da lista
    historico.insert(0, {
        'cidade': dados['cidade'],
        'dados': dados['dados'],
        'url': dados['url'],
        'timestamp_consulta': datetime.now().isoformat()
    })
    
    # Mantém apenas as últimas 100 consultas
    if len(historico) > 100:
        historico = historico[:100]
    
    salvar_historico(historico)

@app.route('/')
def index():
    return render_template('index.html', cidades=CIDADES)

@app.route('/dados/<cidade>', methods=['GET'])
def dados_cidade(cidade):
    """Extrai dados de uma das 5 cidades pelo link fixo"""
    if cidade not in CIDADES:
        return jsonify({'error': 'Cidade não configurada'}), 404

    scraper = IBGEScraper()
    try:
        url = CIDADES[cidade]["url"]
        success = scraper.acessar_link(url)

        if not success:
            return jsonify({'error': f'Falha ao acessar {url}'}), 500

        dados = scraper.extrair_dados_simples()

        resultado = {
            'success': True,
            'cidade': CIDADES[cidade]["nome"],
            'url': url,
            'dados': dados
        }
        
        # Adiciona ao histórico
        adicionar_ao_historico(resultado)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        scraper.fechar()

@app.route('/todas_cidades', methods=['GET'])
def todas_cidades():
    """Extrai dados de todas as cidades de uma vez"""
    resultados = {}
    
    for cidade_key, cidade_info in CIDADES.items():
        scraper = IBGEScraper()
        try:
            success = scraper.acessar_link(cidade_info["url"])
            
            if success:
                dados = scraper.extrair_dados_simples()
                resultado_cidade = {
                    'success': True,
                    'dados': dados,
                    'url': cidade_info["url"]
                }
                resultados[cidade_info["nome"]] = resultado_cidade
                
                # Adiciona cada cidade ao histórico individualmente
                adicionar_ao_historico({
                    'cidade': cidade_info["nome"],
                    'dados': dados,
                    'url': cidade_info["url"]
                })
            else:
                resultados[cidade_info["nome"]] = {
                    'success': False,
                    'error': 'Falha ao acessar a página'
                }
                
        except Exception as e:
            resultados[cidade_info["nome"]] = {
                'success': False,
                'error': str(e)
            }
        finally:
            scraper.fechar()
    
    return jsonify({
        'success': True,
        'resultados': resultados,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/download/csv', methods=['GET'])
def download_csv():
    """Gera e disponibiliza para download um arquivo CSV com o histórico"""
    historico = carregar_historico()
    
    # Criar arquivo CSV temporário
    filename = f"dados_ibge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['cidade', 'localidade', 'populacao', 'ano_censo', 'url', 'timestamp_consulta', 'timestamp_dados']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for registro in historico:
            writer.writerow({
                'cidade': registro['cidade'],
                'localidade': registro['dados']['localidade'],
                'populacao': registro['dados']['populacao'],
                'ano_censo': registro['dados']['ano_censo'],
                'url': registro['url'],
                'timestamp_consulta': registro['timestamp_consulta'],
                'timestamp_dados': registro['dados']['timestamp']
            })
    
    return send_file(filename, as_attachment=True, download_name=filename)

@app.route('/historico', methods=['GET'])
def obter_historico():
    """Retorna o histórico de consultas"""
    historico = carregar_historico()
    return jsonify({
        'success': True,
        'historico': historico,
        'total_registros': len(historico)
    })

@app.route('/limpar_historico', methods=['POST'])
def limpar_historico():
    """Limpa o histórico de consultas"""
    salvar_historico([])
    return jsonify({'success': True, 'message': 'Histórico limpo com sucesso'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)