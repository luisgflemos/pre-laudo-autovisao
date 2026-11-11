"""Consulta de Clientes ERPFlex. Somente GET; senha não persistida."""
import base64,json,ssl,time,queue,threading,urllib.request,urllib.error,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from inspecionar_api_erpflex import NoRedirect,fields_from_json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'work'/'erpflex_clientes'
BASE='https://api.erpflex.com.br/api/clientes'
LIMIT=400

def extract_clients(raw,content_type):
 text=raw.decode('utf-8-sig',errors='replace')
 if 'html' in content_type.lower() or text.lstrip().lower().startswith(('<html','<!doctype html')):raise ValueError('O endereço retornou uma página de acesso, não o cadastro de Clientes.')
 if text.lstrip().startswith('<'):
  root=ET.fromstring(text);flag=root.find('.//error/success')
  if flag is not None and (flag.text or '').lower()=='false':raise ValueError('O ERP recusou a consulta de Clientes.')
  rows=root.findall('.//data/cliente') or root.findall('.//cliente')
  return [{child.tag:child.text for child in row} for row in rows]
 data=json.loads(text)
 if isinstance(data,dict):
  if data.get('status') is False or isinstance(data.get('error'),dict) and str(data['error'].get('success')).lower()=='false':raise ValueError('O ERP recusou a consulta de Clientes.')
  for key in ('clientes','data','cliente'):
   rows=data.get(key)
   if isinstance(rows,list) and all(isinstance(x,dict) for x in rows):return rows
   if isinstance(rows,dict):
    for nested in ('clientes','cliente'):
     value=rows.get(nested)
     if isinstance(value,list) and all(isinstance(x,dict) for x in value):return value
     if isinstance(value,dict):return [value]
  if str(data.get('total'))=='0':return []
 if isinstance(data,list) and all(isinstance(x,dict) for x in data):return data
 raise ValueError('Estrutura retornada não reconhecida como lista de clientes. A consulta precisa ser examinada antes da importação.')

def fetch_clients(username,password,notify,opener=None,sleep=time.sleep):
 auth=base64.b64encode((username+':'+password).encode()).decode('ascii')
 opener=opener or urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 clients=[];fingerprints=set();ids=set();fields={}
 for page in range(250):
  if page:sleep(3.2)
  notify(f'Consultando Clientes: página {page+1}, {len(clients)} registros recebidos...')
  req=urllib.request.Request(BASE+f'?limit={LIMIT}&offset={page*LIMIT}',headers={'Authorization':'Basic '+auth,'Accept':'application/json','Content-Type':'application/json','User-Agent':'PreLaudo-AutoVisao-Clientes/1.0'},method='GET')
  try:
   with opener.open(req,timeout=30) as response:
    raw=response.read(12_000_001)
    if len(raw)>12_000_000:raise ValueError('Página muito grande para importar com segurança. Nenhum catálogo foi substituído.')
    rows=extract_clients(raw,response.headers.get('Content-Type',''))
  except urllib.error.HTTPError as exc:
   code=exc.code;exc.close()
   raise ValueError({401:'Usuário/senha não aceitos na consulta de Clientes.',403:'Usuário sem acesso à consulta de Clientes.',404:'A rota de Clientes não foi encontrada.',429:'Limite da API atingido. Aguarde e tente novamente.'}.get(code,'Falha na consulta de Clientes: HTTP '+str(code)+'.')) from None
  if not rows:break
  fingerprint=json.dumps(rows,sort_keys=True,ensure_ascii=False)
  if fingerprint in fingerprints:raise ValueError('O ERP repetiu uma página. A paginação precisa ser validada antes da importação.')
  fingerprints.add(fingerprint)
  for row in rows:
   identifier=row.get('id') or row.get('ID') or row.get('cliente_id')
   if identifier is not None:
    if str(identifier) in ids:raise ValueError('O ERP retornou um identificador de cliente repetido entre páginas. Importação não aplicada.')
    ids.add(str(identifier))
   fields_from_json(row,found=fields);clients.append(row)
  if len(rows)<LIMIT:break
 else:raise ValueError('Limite de páginas atingido. Importação não aplicada.')
 return clients,fields

def collect(username,password,notify):
 clients,fields=fetch_clients(username,password,notify)
 OUT.mkdir(parents=True,exist_ok=True)
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 data={'consultado_em':datetime.now(timezone.utc).isoformat(),'endpoint':BASE,'usuario':username,'somente_leitura':True,'session_confirmed':False,'total_recebido':len(clients),'campos':fields,'clientes':clients}
 path=OUT/('clientes_'+stamp+'.json');temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
 summary={k:v for k,v in data.items() if k!='clientes'};summary['arquivo_dados']=path.name;summary['modelo_atual_alterado']=False
 (OUT/'resultado.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 return len(clients)

def main():
 import tkinter as tk
 from tkinter import ttk
 app=tk.Tk();app.title('Auto Visão — Clientes do ERP');app.geometry('660x470');app.configure(bg='#f4f4f4')
 frame=tk.Frame(app,bg='white',padx=24,pady=20);frame.pack(fill='both',expand=True,padx=16,pady=16)
 tk.Label(frame,text='Clientes do ERP → Pré-Laudo',font=('Segoe UI',18,'bold'),bg='white').pack(anchor='w')
 tk.Label(frame,text='Consulta e preparação do cadastro para o nosso modelo.',fg='#637084',bg='white').pack(anchor='w',pady=(5,12))
 tk.Label(frame,text=BASE+'\nProdução · somente consulta',bg='#f4f7fb',fg='#4b5565',justify='left',padx=10,pady=10).pack(fill='x',pady=6)
 tk.Label(frame,text='Usuário',bg='white').pack(anchor='w');user=tk.StringVar(value='');ttk.Entry(frame,textvariable=user).pack(fill='x',pady=(3,10))
 tk.Label(frame,text='Senha — digite aqui (não será salva)',bg='white').pack(anchor='w');secret=tk.StringVar();entry=ttk.Entry(frame,textvariable=secret,show='●');entry.pack(fill='x',pady=(3,10))
 state=tk.StringVar(value='Digite a senha e clique em Consultar Clientes.');tk.Label(frame,textvariable=state,bg='white',fg='#4b5565',wraplength=560,justify='left').pack(fill='x',pady=8)
 messages=queue.Queue();busy=False
 def start():
  nonlocal busy
  if busy:return
  password=secret.get();username=user.get().strip()
  if not password or not username:state.set('Informe usuário e senha.');entry.focus_set();return
  busy=True;button.configure(state='disabled');secret.set('')
  def task():
   try:n=collect(username,password,lambda msg:messages.put(('progress',msg)));messages.put(('done',f'Consulta concluída: {n} clientes recebidos. Volte ao chat para conferir o mapeamento.'))
   except ValueError as exc:messages.put(('error',str(exc)))
   except Exception:messages.put(('error','Não foi possível concluir a consulta. Verifique a rede e tente novamente.'))
  threading.Thread(target=task,daemon=True).start()
 def poll():
  nonlocal busy
  try:
   while True:
    kind,text=messages.get_nowait();state.set(text)
    if kind!='progress':busy=False;button.configure(state='normal')
  except queue.Empty:pass
  app.after(200,poll)
 button=tk.Button(frame,text='Consultar Clientes',command=start,bg='#bf1515',fg='white',relief='flat',font=('Segoe UI',11,'bold'),padx=16,pady=10);button.pack(anchor='e',pady=8)
 app.after(200,poll);entry.focus_set();app.mainloop()
if __name__=='__main__':main()
