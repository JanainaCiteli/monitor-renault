import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

def run_renault_test():
    url = "https://store.renault.com.ar/"
    results = []
    
    print(f"Iniciando Playwright em: {url}")

    with sync_playwright() as p:
        # Lança o navegador (headless=True roda em background, sem abrir janela)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Aumenta o timeout padrão para garantir carregamento em conexões lentas
        page.set_default_timeout(60000) 
        
        try:
            page.goto(url)
            
            # O Playwright espera automaticamente a rede ficar ociosa (site carregado)
            page.wait_for_load_state("networkidle")
            
            # Localiza os cards de produtos. 
            # O seletor abaixo busca elementos que tenham classe de item/produto
            # Ajuste o seletor '.item' ou similar conforme a inspeção real do site
            cards = page.locator("div.item, div.card, div.product-item").all()
            
            if not cards:
                print("Cards padrão não encontrados, buscando por títulos...")
                # Estratégia alternativa se a classe mudar
                cards = page.locator("h2:has-text('Renault'), h3:has-text('Renault')").all()

            print(f"Analisando {len(cards)} itens encontrados...")

            for card in cards:
                status = "PASS"
                fail_reasons = []
                name = "N/A"
                price = "N/A"
                img_url = "N/A"

                # 1. Extração e Validação do Nome
                # O Playwright permite encadear locators facilmente
                try:
                    name_el = card.locator("h2, h3, .name").first
                    if name_el.count() > 0:
                        name = name_el.inner_text().strip()
                    else:
                        name = card.inner_text().split('\n')[0]
                    
                    if not name:
                        fail_reasons.append("Nome vazio")
                except:
                    fail_reasons.append("Erro ao ler nome")

                # 2. Extração e Validação de Preço
                try:
                    # Procura texto que contenha $
                    price_str = card.locator(":text-matches('\\$')").first.inner_text()
                    if price_str:
                        price = price_str.strip()
                    else:
                        fail_reasons.append("Preço não visível")
                except:
                    # Em alguns sites, o preço carrega depois ou só no hover
                    fail_reasons.append("Preço não encontrado")

                # 3. Validação de Imagem
                try:
                    img_loc = card.locator("img").first
                    if img_loc.count() > 0:
                        img_url = img_loc.get_attribute("src")
                        # Verifica se a imagem quebrou (tamanho natural é 0)
                        # O JavaScript abaixo roda no navegador para checar a imagem real
                        is_broken = img_loc.evaluate("img => img.naturalWidth === 0")
                        
                        if not img_url or "http" not in img_url:
                            fail_reasons.append("URL de imagem inválida")
                        if is_broken:
                            fail_reasons.append("Imagem quebrada (não renderizou)")
                    else:
                        fail_reasons.append("Tag de imagem ausente")
                except:
                    fail_reasons.append("Erro na imagem")

                # Determina Status Final
                if fail_reasons:
                    status = "FAIL"
                
                results.append({
                    "Data": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "Produto": name,
                    "Preço": price,
                    "Imagem": img_url[:40] + "...",
                    "Status": status,
                    "Detalhes": "; ".join(fail_reasons)
                })

        except Exception as e:
            print(f"Erro na execução: {e}")
        finally:
            browser.close()

    # Gera Relatório
    if results:
        df = pd.DataFrame(results)
        filename = f"report_renault_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        print(f"Relatório gerado: {filename}")
        print(df.head()) # Mostra as primeiras linhas

if __name__ == "__main__":
    run_renault_test()