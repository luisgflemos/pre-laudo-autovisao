"""Consulta fechada, somente GET, das formas de pagamento ERPFlex."""
import json,base64,urllib.request,urllib.error,ssl
from inspecionar_api_erpflex import NoRedirect
URL='https://api.erpflex.com.br/v2/formas_pagamentos'
def fetch_payments(username,password,notify=lambda _:None,opener=None):
 opener=opener or urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 req=urllib.request.Request(URL,headers={'Authorization':'Basic '+base64.b64encode((username+':'+password).encode()).decode(),'Accept':'application/json'},method='GET')
 try:
  with opener.open(req,timeout=30) as response:raw=response.read(2000001)
 except urllib.error.HTTPError as exc:
  code=exc.code;exc.close();raise ValueError('Consulta de pagamentos recusada (HTTP '+str(code)+').') from None
 if len(raw)>2000000:raise ValueError('Resposta excede o limite da consulta.')
 data=json.loads(raw.decode('utf-8-sig'))
 if not isinstance(data,dict) or data.get('status') is not True:raise ValueError('O ERP não confirmou a consulta de pagamentos.')
 rows=data.get('pagamentos')
 if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) for r in rows):raise ValueError('Cadastro vazio ou inválido; base anterior preservada.')
 if int(data.get('total',-1))!=len(rows):raise ValueError('Retorno incompleto das formas de pagamento; base anterior preservada.')
 return rows,1
