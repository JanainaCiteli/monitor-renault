import os
import sys
import datetime
import pandas as pd
from playwright.sync_api import sync_playwright


def run_renault_test():
    # URL do e-comm pode ser configurada por variável de ambiente
    url = os.getenv("ECOMM_URL", "https://store.renault.com.ar/")
    output_dir = "relatorios"
    os.makedirs(output_dir, exist_ok=True)

    results = []
    print(f"Iniciando Playwright em: {url}")

    with sync_playwright() as p:
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(60000)

        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # Fecha banners de consentimento (best-effort)
            for label in ["Aceptar", "Aceitar", "Accept", "OK", "Entendi"]:
                try:
                    page.get_by_role("button", name=label).click(timeout=2000)
                except:
                    pass

            # Scroll para acionar lazy-loading de imagens
            try:
                for _ in range(10):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(500)
                # Volta ao topo para screenshots mais previsíveis
                page.evaluate("window.scrollTo(0, 0)")
            except Exception as e:
                print(f"Falha ao rolar página para lazy-load: {e}")

            # Aguarda pelo menos uma imagem na página
            page.wait_for_selector("img", timeout=60000)

            img_locator = page.locator("img")
            total_imgs = img_locator.count()
            print(f"Total de <img> na página: {total_imgs}")

            vehicle_images = []
            for i in range(total_imgs):
                img = img_locator.nth(i)
                try:
                    visible = img.is_visible()
                    # Largura/altura real carregada (não apenas CSS)
                    natural_width = img.evaluate("el => el.naturalWidth")
                    natural_height = img.evaluate("el => el.naturalHeight")
                    complete = img.evaluate("el => el.complete")
                    # src atual (considera srcset)
                    current_src = img.evaluate("el => el.currentSrc || el.src || ''")
                    # src absoluto
                    absolute_src = page.evaluate("src => new URL(src, document.baseURI).href", current_src) if current_src else ""
                    alt = img.get_attribute("alt") or ""

                    # Heurística simples para filtrar imagens grandes e visíveis, evitando ícones
                    if (
                        visible
                        and complete
                        and natural_width >= 150
                        and natural_height >= 100
                        and absolute_src
                    ):
                        vehicle_images.append({
                            "src": absolute_src,
                            "alt": alt,
                            "width": natural_width,
                            "height": natural_height
                        })
                except Exception as e:
                    # Se uma imagem der erro na avaliação, ignora e continua
                    print(f"Imagem {i} ignorada por erro: {e}")
                    continue

            status = "PASS" if len(vehicle_images) > 0 else "FAIL"
            details = (
                f"{len(vehicle_images)} imagem(ns) de veículo visível(is) detectada(s)."
                if vehicle_images else
                "Nenhuma imagem de veículo visível detectada."
            )

            # Evidência: screenshot da página inteira
            screenshot_path = os.path.join(
                output_dir,
                f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            try:
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"Screenshot salvo em: {screenshot_path}")
            except Exception as e:
                print(f"Falha ao salvar screenshot: {e}")
                screenshot_path = "N/A"

            # Registra resultado (inclui até 5 URLs de imagens para referência)
            img_previews = [vi["src"] for vi in vehicle_images[:5]]
            results.append({
                "Data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "URL": url,
                "QtdImagensVeiculoVisiveis": len(vehicle_images),
                "Status": status,
                "Detalhes": details,
                "Screenshot": screenshot_path,
                "ImagensExemplo": "; ".join(img_previews) if img_previews else ""
            })

        except Exception as e:
            print(f"Erro na execução: {e}")
            # Garante relatório mesmo em caso de erro
            results.append({
                "Data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "URL": url,
                "QtdImagensVeiculoVisiveis": 0,
                "Status": "ERROR",
                "Detalhes": f"Exceção: {e}",
                "Screenshot": "N/A",
                "ImagensExemplo": ""
            })
        finally:
            browser.close()

    # Gera Relatório (sempre)
    df = pd.DataFrame(results)
    filename = os.path.join(
        output_dir,
        f"report_ecomm_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )
    df.to_excel(filename, index=False)
    print(f"Relatório gerado: {filename}")
    print(df.head())

    # Opcional: falhar o pipeline se não tiver imagens de veículo
    fail_on_no_image = os.getenv("FAIL_ON_NO_IMAGE", "false").lower() == "true"
    final_status = results[-1].get("Status", "ERROR")
    if fail_on_no_image and final_status != "PASS":
        print("FAIL_ON_NO_IMAGE=true e nenhuma imagem de veículo detectada. Encerrando com erro.")
        sys.exit(1)


if __name__ == "__main__":
    run_renault_test()
