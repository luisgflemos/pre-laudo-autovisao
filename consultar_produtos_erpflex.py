"""Consulta paginada de produtos/serviços; sem escrita no ERP ou importação de preços."""
import json,base64,urllib.request,urllib.error,ssl,time
from inspecionar_api_erpflex import NoRedirect
URL='https://api.erpflex.com.br/api/produtos/'
def fetch_products(username,password,notify=lambda _:None,opener=None,sleep=time.sleep):
 opener=opener or urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 authorization='Basic '+base64.b64encode((username+':'+password).encode()).decode();rows=[];seen=set();requests=0
 for offset in range(0,100000,50):
  if offset:sleep(3.2)
  notify(f'Consultando produtos e serviços: {len(rows)} itens recebidos...')
  req=urllib.request.Request(URL+f'?limit=50&offset={offset}',headers={'Authorization':authorization,'Accept':'application/json'},method='GET')
  try:
   with opener.open(req,timeout=30) as response:
    raw=response.read(12000001)
    if len(raw)>12000000:raise ValueError('Resposta excede o limite da consulta.')
    data=json.loads(raw.decode('utf-8-sig'));requests+=1
  except urllib.error.HTTPError as exc:
   code=exc.code;exc.close();raise ValueError('Consulta de produtos e serviços recusada (HTTP '+str(code)+').') from None
  if not isinstance(data,dict) or data.get('success') is False or data.get('status') is False:raise ValueError('O ERP não confirmou a consulta de produtos e serviços.')
  page=data.get('data')
  if not isinstance(page,list) or any(not isinstance(x,dict) for x in page):raise ValueError('Formato inválido do cadastro de produtos e serviços.')
  for row in page:
   sid=str(row.get('id') or '')
   if not sid or sid in seen:raise ValueError('Produto/serviço sem ID ou página repetida. Base anterior preservada.')
   seen.add(sid);rows.append(row)
  if len(page)<50:return rows,requests
 raise ValueError('Limite de páginas atingido; catálogo anterior preservado.')
