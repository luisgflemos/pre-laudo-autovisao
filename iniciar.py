"""Inicialização local idempotente: reutiliza o servidor sem encerrar sessões."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8765'
ADMIN=BASE+'/Camada_Intermediaria_v9346_Precos_ERP.html'
OPERATOR=BASE+'/Pre_Laudo_Auto_Visao_v370_Precos_ERP.html'

def server_state(base=BASE, host='127.0.0.1', port=8765):
    try:
        with urllib.request.urlopen(base+'/api/health',timeout=2) as response:
            health=json.load(response)
        if isinstance(health,dict) and health.get('ok') is True and health.get('database')=='pre_laudo_teste.db' and health.get('comprovantes')=='comprovantes':
            return 'running'
    except (OSError,ValueError,urllib.error.URLError):
        pass
    try:
        with socket.create_connection((host,port),timeout=1): return 'occupied'
    except OSError:
        return 'stopped'

def open_chrome(url):
    locations=[Path(os.environ.get(name,''))/'Google/Chrome/Application/chrome.exe' for name in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA') if os.environ.get(name)]
    chrome=next((path for path in locations if path.is_file()),None)
    if chrome:
        try:
            subprocess.Popen([str(chrome),url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            return
        except OSError:
            pass
    print('Abra este endereco no Chrome: '+url)

def ensure_dependency():
    try:
        version=importlib.metadata.version('openai')
        if int(version.split('.')[0])>=2: return True
    except (importlib.metadata.PackageNotFoundError,ValueError):
        pass
    print('Instalando a dependencia OpenAI ausente ou desatualizada...')
    return subprocess.run([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements.txt')],cwd=ROOT).returncode==0

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true',help='Somente verifica a inicializacao, sem abrir navegador ou alterar dados.')
    args=parser.parse_args(argv)
    state=server_state()
    if state=='running':
        print('O Pre-Laudo ja esta em execucao na porta 8765.')
        print('Administracao: '+ADMIN)
        print('Vistoriador: '+OPERATOR)
        if not args.check: open_chrome(ADMIN)
        return 0
    if state=='occupied':
        print('A porta 8765 esta sendo usada por outro servico ou por um servidor sem resposta valida.')
        print('Nenhum processo foi encerrado. Verifique a janela do servidor antes de tentar novamente.')
        return 1
    if args.check:
        print('Servidor parado. Porta 8765 disponivel para iniciar.')
        return 0
    if not ensure_dependency():
        print('Nao foi possivel instalar a dependencia. Verifique sua conexao e tente novamente.')
        return 1
    config=ROOT/'config.env'
    if not config.exists():
        print('Arquivo config.env nao encontrado nesta pasta.')
        return 1
    if 'COLE_SUA_CHAVE_AQUI' in config.read_text(encoding='utf-8'):
        print('Configure sua chave no arquivo config.env antes de iniciar.')
        return 1
    import server
    result=server.main(on_ready=lambda:open_chrome(ADMIN))
    if result and server_state()=='running':
        print('Outra instancia do Pre-Laudo iniciou durante a verificacao. Reutilizando o servidor ativo.')
        open_chrome(ADMIN)
        return 0
    return result

if __name__=='__main__':
    try: sys.exit(main())
    except KeyboardInterrupt:
        print('\nServidor encerrado pelo operador.')

