from flask import Flask, render_template, jsonify, request
import csv
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PLACEHOLDERS = {"seu_usuario_aqui", "sua_senha_aqui", "", "usuario", "senha",
                "seu_usuario", "sua_senha"}

app = Flask(__name__)

BASE_DIR    = Path(__file__).parent
STATUS_DIR  = BASE_DIR / 'status_data'
STATUS_DIR.mkdir(exist_ok=True)

# ── Estado do scraper ────────────────────────────────
scraper_state = {
    'running': False,
    'output':  [],
    'area':    None,
}

# ── Helpers de CSV / Status ──────────────────────────
def get_csv_files():
    files = []
    for f in sorted(BASE_DIR.glob('leads_*.csv')):
        area = f.stem[6:]          # remove 'leads_'
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                count = sum(1 for row in csv.DictReader(fp))
        except Exception:
            count = 0

        # Contagem de prospectados
        sd = load_status(area)
        prospectados = sum(1 for v in sd.values() if v.get('prospectado'))

        files.append({
            'filename':     f.name,
            'area':         area,
            'count':        count,
            'prospectados': prospectados,
        })
    return files


def load_leads(area: str) -> list:
    path = BASE_DIR / f'leads_{area}.csv'
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [dict(row) for row in csv.DictReader(f)]


def load_status(area: str) -> dict:
    path = STATUS_DIR / f'{area}.json'
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_status(area: str, data: dict):
    path = STATUS_DIR / f'{area}.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def apply_auto_update(status_data: dict) -> tuple[dict, bool]:
    """Se 3+ dias em 'contatado' sem avançar → 'sem_resposta'"""
    today   = date.today()
    changed = False
    for info in status_data.values():
        if info.get('status') == 'contatado' and info.get('data_contatado'):
            try:
                dc   = datetime.strptime(info['data_contatado'][:10], '%Y-%m-%d').date()
                if (today - dc).days >= 3:
                    info['status']       = 'sem_resposta'
                    info['data_updated'] = str(today)
                    changed = True
            except Exception:
                pass
    return status_data, changed


# ── Rotas da API ─────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/csvs')
def api_csvs():
    return jsonify(get_csv_files())


@app.route('/api/leads/<area>')
def api_leads(area):
    leads       = load_leads(area)
    status_data = load_status(area)

    status_data, changed = apply_auto_update(status_data)
    if changed:
        save_status(area, status_data)

    result = []
    for lead in leads:
        username = lead.get('username', '').lower().strip()
        info     = status_data.get(username, {})
        result.append({
            **lead,
            'prospectado':   info.get('prospectado', False),
            'status':        info.get('status', ''),
            'data_contatado': info.get('data_contatado', ''),
        })
    return jsonify(result)


@app.route('/api/leads/<area>/<username>', methods=['PUT'])
def api_update_lead(area, username):
    data        = request.json or {}
    status_data = load_status(area)

    if username not in status_data:
        status_data[username] = {}

    info = status_data[username]

    # Toggle prospectado
    if 'prospectado' in data:
        info['prospectado'] = data['prospectado']
        if data['prospectado'] and not info.get('status'):
            info['status'] = 'criado'

    # Troca de status manual
    if 'status' in data:
        info['status']       = data['status']
        info['data_updated'] = str(date.today())
        if data['status'] == 'contatado' and not info.get('data_contatado'):
            info['data_contatado'] = str(date.today())

    save_status(area, status_data)
    return jsonify({'success': True, 'data': info})


@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    if scraper_state['running']:
        return jsonify({'error': 'Busca já em andamento'}), 400

    area = (request.json or {}).get('area', '').strip()
    if not area:
        return jsonify({'error': 'Área não informada'}), 400

    scraper_state.update(running=True, area=area, output=[])

    def run():
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            proc = subprocess.Popen(
                [sys.executable, str(BASE_DIR / 'buscar_leads.py'), area],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                cwd=str(BASE_DIR),
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    scraper_state['output'].append(line)
            proc.wait()
        except Exception as e:
            scraper_state['output'].append(f'ERRO: {e}')
        finally:
            scraper_state['running'] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True})


@app.route('/api/buscar/status')
def api_buscar_status():
    return jsonify({
        'running': scraper_state['running'],
        'area':    scraper_state['area'],
        'output':  scraper_state['output'][-60:],
    })


@app.route('/api/credentials-status')
def api_credentials_status():
    """Le o .env na hora para checar se credenciais foram preenchidas."""
    from dotenv import dotenv_values
    env_path = BASE_DIR / '.env'
    vals     = dotenv_values(env_path) if env_path.exists() else {}
    username = vals.get('INSTAGRAM_USERNAME', '').strip()
    password = vals.get('INSTAGRAM_PASSWORD', '').strip()
    configured = username not in PLACEHOLDERS and password not in PLACEHOLDERS
    return jsonify({
        'configured': configured,
        'username':   username if configured else None,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
