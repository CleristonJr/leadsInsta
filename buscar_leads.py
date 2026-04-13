import sys
import os
import csv
import time
import random
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# ── UTF-8 no terminal Windows ───────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

BASE_DIR  = Path(__file__).parent
USERNAME  = os.getenv("INSTAGRAM_USERNAME", "").strip()
PASSWORD  = os.getenv("INSTAGRAM_PASSWORD", "").strip()
MAX_LEADS = int(os.getenv("MAX_LEADS", 20))
DELAY_MIN = float(os.getenv("DELAY_MIN", 3))
DELAY_MAX = float(os.getenv("DELAY_MAX", 7))

PLACEHOLDERS = {"seu_usuario_aqui", "sua_senha_aqui", "", "usuario", "senha",
                "seu_usuario", "sua_senha"}

# ── Hashtags por área ───────────────────────────────
HASHTAGS_POR_AREA = {
    "dentista":       ["dentista", "odontologia", "dentistabrasil", "sorrisoperfeito", "clinicaodontologica"],
    "nutricionista":  ["nutricionista", "nutricao", "alimentacaosaudavel", "nutricaobrasil", "dietabrasil"],
    "personal":       ["personaltrainer", "personalfit", "treinopersonal", "fitness", "treinadorpessoal"],
    "advogado":       ["advogado", "direito", "advocacia", "advogadobrasil", "juridico"],
    "psicologo":      ["psicologo", "psicologia", "saudemental", "terapia", "psicologobrasil"],
    "medico":         ["medico", "medicina", "saude", "medicobrasil", "clinicamedica"],
    "arquiteto":      ["arquiteto", "arquitetura", "designdeinteriores", "arquiteturabrasil"],
    "contador":       ["contador", "contabilidade", "contadorbrasil", "financas"],
    "corretor":       ["corretordeimoveis", "imobiliaria", "mercadoimobiliario", "casas"],
    "coach":          ["coach", "coaching", "mentoria", "lideranca", "desenvolvimentopessoal"],
    "fotografo":      ["fotografo", "fotografia", "fotografiabrasil", "ensaio"],
    "designer":       ["designer", "designgrafico", "branding", "identidadevisual"],
    "veterinario":    ["veterinario", "veterinaria", "petshop", "clinicavet"],
    "esteticista":    ["esteticista", "estetica", "skincare", "beleza"],
    "fisioterapeuta": ["fisioterapeuta", "fisioterapia", "reabilitacao", "fisiofit"],
    "engenheiro":     ["engenheiro", "engenharia", "construcao", "obra"],
}


def get_hashtags(area: str) -> list:
    a = area.lower().strip()
    for key, tags in HASHTAGS_POR_AREA.items():
        if key in a or a in key:
            return tags
    slug = a.replace(" ", "")
    return [slug, slug + "brasil", slug + "br"]


# ── CSV helpers ─────────────────────────────────────
def carregar_csv(path: Path) -> set:
    existentes = set()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if "username" in row:
                    existentes.add(row["username"].strip().lower())
        print(f"[INFO] {len(existentes)} leads ja existentes no CSV.")
    return existentes


def salvar_lead(path: Path, username: str, link: str):
    novo = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["username", "link_perfil", "data_encontrado"])
        if novo:
            w.writeheader()
        w.writerow({"username": username, "link_perfil": link,
                    "data_encontrado": str(date.today())})


# ── Criar driver ─────────────────────────────────────
def criar_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def _url_segura(driver) -> str:
    """Retorna current_url sem explodir se o browser fechou."""
    try:
        return driver.current_url
    except Exception:
        return ""


# ── Login robusto ────────────────────────────────────
def fazer_login(driver: webdriver.Chrome) -> bool:
    print("[BROWSER] Abrindo Instagram...")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(4)

    # Ja esta logado?
    if "accounts/login" not in _url_segura(driver):
        print("[OK] Sessao ativa, sem necessidade de novo login.")
        return True

    # Aceitar cookies (varias versoes do banner)
    for texto in ["Allow all cookies", "Aceitar todos os cookies",
                  "Allow essential and optional cookies", "Permitir"]:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(),'{texto}')]"))
            )
            btn.click()
            time.sleep(1)
            break
        except Exception:
            pass

    # ── Campo usuario (falha nao cancela) ───────────
    try:
        user_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.NAME, "username"))
        )
        user_field.click()
        user_field.clear()
        for ch in USERNAME:
            user_field.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.11))
        time.sleep(0.5)
    except Exception as e:
        print(f"[AVISO] Campo usuario: {type(e).__name__}")

    # ── Campo senha (falha nao cancela) ─────────────
    try:
        pass_field = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.NAME, "password"))
        )
        pass_field.click()
        for ch in PASSWORD:
            pass_field.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.11))
        time.sleep(0.5)
    except Exception as e:
        print(f"[AVISO] Campo senha: {type(e).__name__}")

    # ── Clicar Entrar (falha nao cancela) ───────────
    try:
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        print("[BROWSER] Aguardando navegacao apos login...")
    except Exception as e:
        print(f"[AVISO] Botao submit: {type(e).__name__}")

    # ── Aguardar saida da pagina de login (ate 20s) ─
    # Sucesso = URL mudou, independente de erros anteriores
    for _ in range(20):
        time.sleep(1)
        cur = _url_segura(driver)
        if not cur or "accounts/login" not in cur:
            break

    cur = _url_segura(driver)

    # Falhou: ainda na pagina de login
    if "accounts/login" in cur:
        print("[ERRO] Login falhou. Verifique usuario e senha no .env")
        return False

    # Checkpoint / 2FA
    if "challenge" in cur or "checkpoint" in cur:
        print("[AVISO] Instagram pediu verificacao adicional.")
        print("[AGUARDANDO] Complete no browser. Aguardando ate 90s...")
        for _ in range(90):
            time.sleep(1)
            cur = _url_segura(driver)
            if not cur:
                break
            if "challenge" not in cur and "checkpoint" not in cur:
                print("[OK] Verificacao concluida!")
                break
        else:
            print("[ERRO] Tempo esgotado aguardando verificacao.")
            return False

    time.sleep(2)

    # ── Popups pos-login (nao fatal) ─────────────────
    for _ in range(4):
        try:
            btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(text(),'Not now') or contains(text(),'Not Now') "
                "or contains(text(),'Agora não') or contains(text(),'Não agora') "
                "or contains(text(),'Agora nao') or contains(text(),'Nao agora')]"
            )))
            btn.click()
            time.sleep(2)
        except Exception:
            break

    print(f"[OK] Logado com sucesso como @{USERNAME}")
    return True


# ── Busca por hashtag (browser real) ────────────────
def buscar_na_hashtag(driver: webdriver.Chrome, hashtag: str,
                      existentes: set, falta: int, csv_path: Path) -> int:
    coletados = 0
    url = f"https://www.instagram.com/explore/tags/{hashtag}/"
    print(f"\n[BROWSER] Acessando #{hashtag}...")
    driver.get(url)
    time.sleep(4)

    cur = _url_segura(driver)
    if "login" in cur:
        print(f"  [AVISO] Redirecionado para login em #{hashtag}")
        return 0

    # Coletar links de posts com scroll
    post_links = []
    for scroll in range(5):
        els = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
        for el in els:
            try:
                href = el.get_attribute("href")
                if href and href not in post_links:
                    post_links.append(href)
            except Exception:
                continue
        if len(post_links) >= falta * 4:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(1.5, 2.5))

    print(f"  [INFO] {len(post_links)} posts encontrados em #{hashtag}")

    # Visitar cada post e extrair autor
    for post_url in post_links:
        if coletados >= falta:
            break
        try:
            driver.get(post_url)
            time.sleep(random.uniform(2, 4))

            username = None

            for sel in ["article header a[href]", "header a[role='link']", "h2 a", "a.notranslate"]:
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, sel)
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if "instagram.com/" in href and "/p/" not in href:
                            candidate = href.rstrip("/").split("/")[-1].lower()
                            if candidate and candidate not in {"explore", "reels", "stories", ""}:
                                username = candidate
                                break
                    if username:
                        break
                except Exception:
                    continue

            if username and username not in existentes:
                link = f"https://www.instagram.com/{username}/"
                salvar_lead(csv_path, username, link)
                existentes.add(username)
                coletados += 1
                print(f"  [+] [{coletados}/{falta}] @{username}")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        except Exception as e:
            print(f"  [AVISO] Erro ao processar post: {type(e).__name__}")
            continue

    return coletados


# ── Principal ────────────────────────────────────────
def buscar_leads(area: str):
    if USERNAME in PLACEHOLDERS or PASSWORD in PLACEHOLDERS:
        print("[ERRO] Configure INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no arquivo .env")
        sys.exit(1)

    area_slug = area.lower().strip().replace(" ", "_")
    csv_path  = BASE_DIR / f"leads_{area_slug}.csv"

    print(f"\n{'='*50}")
    print(f"  Buscando leads: {area.upper()}")
    print(f"  Arquivo: {csv_path.name}")
    print(f"{'='*50}\n")

    existentes = carregar_csv(csv_path)
    hashtags   = get_hashtags(area)
    print(f"[INFO] Hashtags: {', '.join(['#' + h for h in hashtags])}")

    driver = criar_driver()
    try:
        if not fazer_login(driver):
            print("[ERRO] Login nao realizado. Busca cancelada.")
            sys.exit(1)

        novos = 0
        for ht in hashtags:
            if novos >= MAX_LEADS:
                break
            novos += buscar_na_hashtag(driver, ht, existentes,
                                       MAX_LEADS - novos, csv_path)

        print(f"\n{'='*50}")
        print(f"  Concluido! {novos} novos leads adicionados.")
        print(f"  Arquivo: {csv_path.name}")
        print(f"{'='*50}\n")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# ────────────────────────────────────────────────────
if __name__ == "__main__":
    area_input = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else \
                 input("Area profissional (ex: dentista): ").strip()
    if not area_input:
        print("[ERRO] Nenhuma area informada.")
        sys.exit(1)
    buscar_leads(area_input)
