"""Inspeção manual ERPFlex: exclusivamente GET, senha somente em memória."""
import base64,json,re,ssl,time,threading,queue,urllib.request,urllib.error,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'work'/'erpflex_inspecao'
ENVIRONMENTS={
 'Produção — consulta somente':('https://api.erpflex.com.br/v1','https://api.erpflex.com.br/v2'),
 'Sandbox — testes':('https://sandbox.erpflex.com.br/api','https://sandbox.erpflex.com.br/api_v2'),
 'Produção LW — consulta somente':('https://apilw.erpflex.com.br/v1','https://apilw.erpflex.com.br/v2')}
RESOURCES=[('Clientes',0,'/clientes?limit=1&offset=0'),('Serviços',1,'/servicos'),('Formas de pagamento',1,'/formas_pagamentos'),('Operadores',1,'/operador'),('Vendedores',0,'/vendedores'),('Campos de ordens de serviço',1,'/os/options')]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def fields_from_json(value,path='',found=None,depth=0):
 found={} if found is None else found
 if depth>16:return found
 if isinstance(value,dict):
  for key,item in value.items():
   name=str(key)[:140];new=f'{path}.{name}' if path else name
   found[new]=type(item).__name__
   fields_from_json(item,new,found,depth+1)
 elif isinstance(value,list):
  for item in value[:10]:fields_from_json(item,path+'[]',found,depth+1)
 return found

def schema_descriptors(value,path='',result=None):
 result=[] if result is None else result
 if isinstance(value,dict):
  if 'alias' in value and any(k in value for k in ('type','required','description')):
   result.append({'field':path,**{k:v for k,v in value.items() if k in ('alias','description','type','format','size','required') and isinstance(v,(str,int,bool))}})
  for key,item in value.items():schema_descriptors(item,path+'.'+str(key) if path else str(key),result)
 elif isinstance(value,list):
  for item in value[:10]:schema_descriptors(item,path+'[]',result)
 return result

def decode_schema(raw,ctype):
 text=raw.decode('utf-8-sig',errors='replace')
 if 'html' in ctype.lower() or text.lstrip().lower().startswith(('<!doctype html','<html')):raise ValueError('Resposta HTML; endereço ou acesso precisa ser verificado.')
 if text.lstrip().startswith('<'):
  root=ET.fromstring(text)
  flag=root.find('.//error/success')
  if flag is not None and (flag.text or '').lower()=='false':raise ValueError('A API retornou erro; nenhum dado foi gravado.')
  fields={}
  def walk(el,path=''):
   name=el.tag.split('}')[-1];path=path+'.'+name if path else name;fields[path]='elemento';
   for child in list(el)[:30]:walk(child,path)
  walk(root);return fields,'XML',[]
 value=json.loads(text)
 if not isinstance(value,(dict,list)):raise ValueError('Resposta não reconhecida como catálogo da API.')
 if isinstance(value,dict) and (value.get('status') is False or isinstance(value.get('error'),dict) and str(value['error'].get('success')).lower()=='false'):raise ValueError('A API retornou erro; nenhum dado foi gravado.')
 return fields_from_json(value),'JSON',schema_descriptors(value.get('options',{})) if isinstance(value,dict) else []

def inspect_resource(url,username,password,opener=None):
 # A lista fechada impede envio acidental de credenciais a outro destino.
 allowed=tuple(base+'/' for pair in ENVIRONMENTS.values() for base in pair)
 if not url.startswith(allowed):raise ValueError('Destino não pertence aos endereços oficiais configurados.')
 auth=base64.b64encode((username+':'+password).encode('utf-8')).decode('ascii')
 req=urllib.request.Request(url,headers={'Authorization':'Basic '+auth,'Accept':'application/json','Content-Type':'application/json','User-Agent':'PreLaudo-AutoVisao-Consulta/1.0'},method='GET')
 opener=opener or urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 try:
  with opener.open(req,timeout=25) as response:
   raw=response.read(2_000_001)
   if len(raw)>2_000_000:return {'http':response.status,'ok':False,'message':'Resposta excede o limite da inspeção.'}
   fields,fmt,descriptors=decode_schema(raw,response.headers.get('Content-Type',''))
   return {'http':response.status,'ok':True,'format':fmt,'fields':fields,'field_count':len(fields),'schema_descriptors':descriptors}
 except urllib.error.HTTPError as e:
  e.close()
  return {'http':e.code,'ok':False,'message':{401:'Usuário/senha não aceitos neste ambiente.',403:'Acesso recusado neste recurso.',404:'Rota não localizada neste ambiente.',429:'Limite de requisições atingido.'}.get(e.code,'A API recusou a consulta (HTTP '+str(e.code)+').')}
 except (ValueError,ET.ParseError):return {'http':200,'ok':False,'message':'A resposta não confirmou acesso ao catálogo; verificar ambiente e permissões.'}
 except (urllib.error.URLError,TimeoutError,OSError):return {'http':None,'ok':False,'message':'Não foi possível conectar. Verifique a rede ou o ambiente e tente novamente.'}

def run_inspection(environment,username,password,notify):
 OUT.mkdir(parents=True,exist_ok=True)
 report={'started_at':datetime.now(timezone.utc).isoformat(),'environment':environment,'username':username,'expected_session_cnpj':'20682034000110','session_confirmed':False,'mode':'GET somente; sem alteração ou sincronização','results':[]}
 for index,(name,version,path) in enumerate(RESOURCES):
  if index:time.sleep(3.2)
  url=ENVIRONMENTS[environment][version]+path
  notify(f'Consultando {name.lower()}...')
  result=inspect_resource(url,username,password);report['results'].append({'resource':name,'url':url,**result})
  (OUT/'resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  if result.get('http') in (401,403,429) and index==0:break
 lines=['INSPEÇÃO ERPFLEX — SOMENTE LEITURA',f'Ambiente: {environment}',f'Usuário: {username}','Sessão desejada: Consolidadora — CNPJ 20.682.034/0001-10.','Vínculo da empresa ainda não confirmado por esta inspeção.','A senha e os valores dos cadastros não foram gravados.','']
 for result in report['results']:
  lines += [result['resource'],result['url'],f"HTTP: {result['http']} — "+('Consulta aceita' if result['ok'] else result['message'])]
  lines.extend('  Especificação: '+json.dumps(descriptor,ensure_ascii=False) for descriptor in result.get('schema_descriptors',[]))
  lines.extend('  '+field+' : '+kind for field,kind in result.get('fields',{}).items());lines.append('')
 (OUT/'campos_disponiveis.txt').write_text('\n'.join(lines),encoding='utf-8')
 return report

def main():
 import tkinter as tk
 from tkinter import ttk
 app=tk.Tk();app.title('Auto Visão — Checagem da API ERPFlex');app.geometry('660x560');app.configure(bg='#f4f4f4')
 frame=tk.Frame(app,bg='white',padx=24,pady=20);frame.pack(fill='both',expand=True,padx=16,pady=16)
 tk.Label(frame,text='Checagem de acesso à API',font=('Segoe UI',18,'bold'),bg='white',fg='#1a1a1a').pack(anchor='w')
 tk.Label(frame,text='Consultas de estrutura e campos. Não envia OS nem altera cadastros.',bg='white',fg='#637084',wraplength=570,justify='left').pack(anchor='w',pady=(6,14))
 tk.Label(frame,text='Ambiente',bg='white').pack(anchor='w');environment=tk.StringVar(value=next(iter(ENVIRONMENTS)));env=ttk.Combobox(frame,textvariable=environment,values=list(ENVIRONMENTS),state='readonly');env.pack(fill='x',pady=(3,10))
 tk.Label(frame,text='Usuário da API',bg='white').pack(anchor='w');user=tk.StringVar(value='');ttk.Entry(frame,textvariable=user).pack(fill='x',pady=(3,10))
 tk.Label(frame,text='Senha — digite aqui (não será salva)',bg='white').pack(anchor='w');secret=tk.StringVar();entry=ttk.Entry(frame,textvariable=secret,show='●');entry.pack(fill='x',pady=(3,10))
 tk.Label(frame,text='Sessão desejada: CONSOLIDADORA — CNPJ 20.682.034/0001-10\nO vínculo será confirmado a partir do que a API permitir consultar.',bg='#f4f7fb',fg='#4b5565',justify='left',padx=10,pady=10,wraplength=560).pack(fill='x',pady=8)
 status=tk.StringVar(value='Pronto. Digite a senha e clique em Consultar acesso e campos.');tk.Label(frame,textvariable=status,bg='white',fg='#4b5565',wraplength=560,justify='left').pack(fill='x',pady=8)
 messages=queue.Queue();busy=False
 def start():
  nonlocal busy
  if busy:return
  password=secret.get();username=user.get().strip();selected_env=environment.get()
  if not password or not username:status.set('Informe o usuário e a senha.');entry.focus_set();return
  busy=True;button.configure(state='disabled');env.configure(state='disabled');secret.set('')
  def task():
   try:
    report=run_inspection(selected_env,username,password,lambda msg:messages.put(('progress',msg)))
    messages.put(('done',report))
   except Exception:messages.put(('error','Falha na inspeção. A senha não foi gravada.'))
  threading.Thread(target=task,daemon=True).start()
 def poll():
  nonlocal busy
  try:
   while True:
    kind,data=messages.get_nowait()
    if kind=='progress':status.set(data)
    else:
     busy=False;button.configure(state='normal');env.configure(state='readonly')
     if kind=='error':status.set(data)
     else:
      good=sum(r['ok'] for r in data['results']);status.set(f'Concluído: {good} de {len(data["results"])} consultas aceitas.\nRelatório salvo na pasta work/erpflex_inspecao. Pode voltar ao chat.' if good else 'Acesso não validado. '+data['results'][0].get('message','Verifique o ambiente.'))
  except queue.Empty:pass
  app.after(200,poll)
 button=tk.Button(frame,text='Consultar acesso e campos',command=start,bg='#bf1515',fg='white',font=('Segoe UI',11,'bold'),relief='flat',padx=14,pady=10);button.pack(anchor='e',pady=10)
 app.after(200,poll);entry.focus_set();app.mainloop()
if __name__=='__main__':main()
