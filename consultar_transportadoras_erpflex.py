"""Transportadoras ERPFlex: somente GET, paginação oficial de dez registros."""
import json,base64,urllib.request,urllib.error,ssl,time
from inspecionar_api_erpflex import NoRedirect
URL='https://api.erpflex.com.br/api/transportadoras'
def fetch_carriers(username,password,notify=lambda _:None,opener=None,sleep=time.sleep,first_page=None):
 opener=opener or urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 auth='Basic '+base64.b64encode((username+':'+password).encode()).decode();rows=[];seen=set();requests=0
 for offset in range(0,100000,10):
  if offset==0 and first_page is not None:data=first_page;requests+=1
  else:
   if offset:sleep(3.2)
   req=urllib.request.Request(URL+('/'+str(offset) if offset else ''),headers={'Authorization':auth,'Accept':'application/json'},method='GET')
   try:
    with opener.open(req,timeout=30) as response:raw=response.read(2000001)
   except urllib.error.HTTPError as exc:
    code=exc.code;exc.close();raise ValueError('Consulta de transportadoras recusada (HTTP '+str(code)+').') from None
   if len(raw)>2000000:raise ValueError('Resposta excede limite da consulta.')
   data=json.loads(raw.decode('utf-8-sig'));requests+=1
  if not isinstance(data,dict) or data.get('success') not in (True,1):raise ValueError('O ERP não confirmou a consulta de transportadoras.')
  page=data.get('data')
  if not isinstance(page,list) or any(not isinstance(r,dict) for r in page):raise ValueError('Formato inválido de transportadoras.')
  for row in page:
   sid=str(row.get('id') or '').strip()
   if not sid or sid in seen:raise ValueError('ID ausente ou paginação repetida; base anterior preservada.')
   seen.add(sid);rows.append(row)
  if len(page)<10:
   if not rows:raise ValueError('Cadastro vazio; base anterior preservada.')
   return rows,requests
 raise ValueError('Limite de páginas atingido; catálogo anterior preservado.')
