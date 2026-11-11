"""Preços das variantes ERP; numeração de tabela preservada, dinheiro em centavos."""
import json,re
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from datetime import datetime,timezone

def init(con):
 con.execute('CREATE TABLE IF NOT EXISTS erp_precos(service_erp_id TEXT PRIMARY KEY,data_json TEXT NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS erp_precos_estado(id INTEGER PRIMARY KEY CHECK(id=1),data_json TEXT NOT NULL)')
def snapshot(con):
 if not con.execute("SELECT 1 FROM sqlite_master WHERE name='erp_precos_estado'").fetchone():return None
 row=con.execute('SELECT data_json FROM erp_precos_estado WHERE id=1').fetchone();return json.loads(row[0]) if row else None
def cached(con):
 if not (snapshot(con) or {}).get('ultima_atualizacao'):return None
 return {r['code']:r for r in (json.loads(row[0]) for row in con.execute('SELECT data_json FROM erp_precos'))}
def cents(value):
 try:amount=Decimal(str(value))
 except InvalidOperation:raise ValueError('Preço monetário inválido.') from None
 if not amount.is_finite() or amount<0:raise ValueError('Preço negativo ou não finito.')
 return int((amount*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def prepare(rows):
 from produtos_erp import is_service
 services=[r for r in rows if is_service(r) and str(r.get('ativo_inativo'))=='1']
 if not services:raise ValueError('Nenhum serviço ativo para importar preços; base anterior preservada.')
 codes=[str(r.get('codigo') or '').strip() for r in services]
 if len(codes)!=len(set(codes)):raise ValueError('Código de serviço ativo duplicado; preços não importados.')
 result=[]
 for row,code in zip(services,codes):
  variants=[v for v in row.get('variantes',[]) if str(v.get('ativo'))=='S']
  if len(variants)!=1 or not variants[0].get('id'):raise ValueError('Variante ativa ausente ou ambígua para '+code+'. Preços não importados.')
  variant=variants[0];prices=variant.get('precos')
  if not isinstance(prices,dict):raise ValueError('Matriz de preços ausente para '+code)
  values={}
  for key,value in prices.items():
   if re.fullmatch(r'tabela_\d+',key):
    index=int(key[7:])
    if index>10000:raise ValueError('Número de tabela fora do limite suportado.')
    values[str(index)]=cents(value)
  if not values or int(prices.get('tabelas',-1))!=len(values):raise ValueError('Matriz de preços incompleta para '+code)
  last=max(map(int,values))
  result.append({'code':code,'service_erp_id':str(row['id']),'variant_erp_id':str(variant['id']),'by_table_cents':values,'standard':values.get('0',0)/100,'tables':[values.get(str(i),0)/100 for i in range(1,last+1)],'origem':'ERPFlex /api/produtos/ → variantes.precos','ultima_atualizacao':datetime.now(timezone.utc).isoformat()})
 return result

def apply(con,rows,requests=0):
 init(con);items=prepare(rows)
 con.execute('DELETE FROM erp_precos')
 for item in items:con.execute('INSERT INTO erp_precos VALUES(?,?)',(item['service_erp_id'],json.dumps(item,ensure_ascii=False)))
 numbers=sorted({int(n) for item in items for n in item['by_table_cents']})
 state={'ultima_atualizacao':datetime.now(timezone.utc).isoformat(),'servicos_com_precos':len(items),'valores':sum(len(item['by_table_cents']) for item in items),'quantidade_tabelas':len(numbers),'numeros_tabelas':numbers,'maior_numero_tabela':max(numbers),'requisicoes_compartilhadas_produtos':requests,'regra':'Preço do cliente ausente ou zero utiliza Tabela Padrão; permissões manuais por cliente preservadas.'}
 con.execute('INSERT OR REPLACE INTO erp_precos_estado VALUES(1,?)',(json.dumps(state,ensure_ascii=False),));return state

def detail(price,client):
 index=int(client.get('price_index') or 0)
 if index<0:raise ValueError('Número de tabela de preços inválido.')
 particular=client.get('type')=='PARTICULAR' or str(client.get('name','')).strip().lower()=='particular'
 requested=0 if particular else index
 if 'by_table_cents' in price:
  values=price['by_table_cents'];standard=int(values.get('0',0));specific=int(values.get(str(requested),0))
 else:
  standard=cents(price.get('standard') or 0);tables=price.get('tables') or [];specific=cents(tables[index-1]) if index>0 and index<=len(tables) else 0
 applied=requested if requested and specific>0 else 0
 value=specific if applied else standard
 fallback=bool(requested and not applied)
 source='TABELA_CLIENTE' if applied else 'TABELA_PADRAO_FALLBACK' if fallback else 'TABELA_PADRAO'
 return {'cents':value,'source':source,'table_requested':requested,'table_applied':applied,'fallback':fallback,'variant_erp_id':price.get('variant_erp_id'),'service_erp_id':price.get('service_erp_id'),'ultima_atualizacao':price.get('ultima_atualizacao')}
