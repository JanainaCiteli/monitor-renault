import datetime
import os
import pandas as pd
from playwright.sync_api import sync_playwright

def run_renault_test():
    url = "https://store.renault.com.ar/"
    results = []
    
    print(f"Iniciando Playwright em: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Aumentei o tempo de espera para 60 segundos
        page.set_default_timeout(60000) 
        
        try:
            page.goto(url)
            # Espera forçada para garantir carregamento visual
            page.wait_for_timeout(5000) 
            
            # Tenta seletores mais abrangentes
            cards = page.locator("div.item, div.card, div.product-item, div[class*='product']").all()
            
            # Se não achar por classe, tenta achar qualquer coisa com preço
            if not cards:
                print("Tentando estratégia de backup...")
                cards = page.locator("xpath=//div[contains(., '$')]").all()

            print(f"DEBUG: Encontrados {len(cards)} elementos potenciais.")

            if len(cards) == 0:
                # Se não achar nada, adiciona um registro de erro no Excel
                results.append({
                    "Data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Produto": "ERRO",
                    "Status": "FAIL",
                    "Detalhes": "Nenhum produto encontrado na página. Verificar seletores."
                })

            for card in cards:
                # Lógica simplificada para extrair texto
                text_content = card.inner_text().replace('\n', ' ')
                
                results.append({
                    "Data": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "Produto": text_content[:50], # Pega os primeiros 50 caracteres
                    "Status": "PASS" if "$" in text_content else "CHECK",
                    "Detalhes": "Item capturado"
                })

        except Exception as e:
            print(f"Erro Crítico: {e}")
            results.append({
                "Data": datetime.datetime.now().strftime("%Y-%m-%d"),
                "Produto": "ERRO DE EXECUÇÃO",
                "Status": "CRITICAL",
                "Detalhes": str(e)
            })
        finally:
            browser.close()

    # --- PARTE IMPORTANTE: SALVAR SEMPRE ---
    print("Gerando relatório...")
    
    # Cria um DataFrame mesmo se estiver vazio
    if not results:
        results = [{"Status": "Nenhum dado", "Detalhes": "Lista vazia"}]

    df = pd.DataFrame(results)
    
    # Nome fixo ou dinâmico simples
    filename = "relatorio_renault.xlsx"
    
    # Salva o arquivo
    df.to_excel(filename, index=False)
    
    # Confirmação no log que o arquivo existe
    if os.path.exists(filename):
        print(f"SUCESSO: Arquivo {filename} criado com sucesso.")
    else:
        print("ERRO: Falha ao criar arquivo no disco.")

if __name__ == "__main__":
    run_renault_test()
