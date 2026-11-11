"""Relação local de Empresas/Unidades. Não sincroniza nem escreve no ERPFlex."""
import json
from datetime import datetime,timezone

def init(con):
 con.execute('CREATE TABLE IF NOT EXISTS erp_empresas(erp_id TEXT PRIMARY KEY, nome TEXT NOT NULL, ativa_operacional INTEGER NOT NULL CHECK(ativa_operacional IN (0,1)), papel TEXT NOT NULL, data_json TEXT NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS erp_empresas_estado(id INTEGER PRIMARY KEY CHECK(id=1), data_json TEXT NOT NULL)')

def cached(con):
 if not con.execute("SELECT 1 FROM sqlite_master WHERE name='erp_empresas'").fetchone():return None
 rows=con.execute('SELECT data_json FROM erp_empresas ORDER BY nome').fetchall()
 return [json.loads(r[0]) for r in rows] if rows else None

def unidades(con):
 rows=cached(con)
 if rows is None:return None
 return [{'id':r['erp_id'],'erp_id':r['erp_id'],'nome':r['nome']} for r in rows if r['ativa_operacional'] and r['papel']=='UNIDADE']

def apply(con,rows):
 ids=[r['erp_id'] for r in rows]
 if not rows or len(ids)!=len(set(ids)):raise ValueError('Empresas vazias ou com IDs duplicados.')
 for r in rows:
  if not str(r['erp_id']).isdigit() or not r['nome'].strip() or r['papel'] not in ('UNIDADE','CONSOLIDADORA'):raise ValueError('Empresa inválida.')
  if r['papel']=='CONSOLIDADORA' and r['ativa_operacional']:raise ValueError('Consolidadora não é unidade operacional.')
 init(con)
 for r in rows:
  con.execute('INSERT OR REPLACE INTO erp_empresas VALUES(?,?,?,?,?)',(r['erp_id'],r['nome'],int(r['ativa_operacional']),r['papel'],json.dumps(r,ensure_ascii=False)))
 state={'atualizado_em':datetime.now(timezone.utc).isoformat(),'origem':'Relação inicial validada com cadastro local, imagens e orçamentos; situação operacional confirmada pelo usuário','sincronizacao_automatica':False,'gravacao_multiempresa_validada':False}
 con.execute('INSERT OR REPLACE INTO erp_empresas_estado VALUES(1,?)',(json.dumps(state,ensure_ascii=False),))
 return state
