"""Configuração e avaliação central das regras da OS (valores em centavos)."""
import copy
import json
import re
import unicodedata
from datetime import datetime, timezone

DEFAULTS = {
    'clients': {}, 'payments': {}, 'validity_minutes': 30, 'require_crlv': True,
    'tolerance_cents': 0, 'block_duplicates': True, 'cash_review': True,
    'approval_reason': True,
    'justifications': {'proof': True, 'financial': True, 'other': True},
    'actions': {'value': 'REVIEW', 'time': 'REVIEW', 'method': 'REVIEW', 'zero': 'REVIEW'},
    'erp': {'automatic': True, 'sync_minutes': 15, 'attempts': 3, 'retry_minutes': 5},
}

def normalize(value):
    return re.sub('[^A-Z0-9]', '', unicodedata.normalize('NFD', str(value or '').upper()))

def payment_rule(config, key):
    if key == 'DINHEIRO': return {'proof': False, 'identifier': False}
    return {'proof': key != 'DINHEIRO', 'identifier': key != 'DINHEIRO', **config['payments'].get(key, {})}

def validate(config):
    if isinstance(config,dict) and 'require_crlv' not in config:
        config={**config,'require_crlv':True}
    if isinstance(config,dict) and 'justifications' not in config:
        config={**config,'justifications':{key:config.get('approval_reason',True) for key in ('proof','financial','other')}}
    if not isinstance(config, dict):
        raise ValueError('Configuração ausente ou inválida: esperado um objeto com os parâmetros.')
    if set(config) != set(DEFAULTS):
        missing=sorted(set(DEFAULTS)-set(config));extra=sorted(set(config)-set(DEFAULTS))
        detail=[]
        if missing: detail.append('campos ausentes: '+', '.join(missing))
        if extra: detail.append('campos desconhecidos: '+', '.join(extra))
        raise ValueError('Estrutura de parâmetros inválida ('+'; '.join(detail)+'). Recarregue a tela para atualizar os campos.')
    for key in ('validity_minutes', 'tolerance_cents'):
        if type(config[key]) is not int or not 0 <= config[key] <= 100000000:
            raise ValueError('Janela e tolerância devem ser inteiros não negativos.')
    for key in ('block_duplicates', 'cash_review', 'approval_reason', 'require_crlv'):
        if type(config[key]) is not bool: raise ValueError('Opção booleana inválida.')
    reasons=config['justifications']
    if not isinstance(reasons,dict) or set(reasons)!={'proof','financial','other'} or any(type(v) is not bool for v in reasons.values()):
        raise ValueError('As três opções de justificativa devem ser Sim/Não.')
    if not isinstance(config['actions'], dict) or set(config['actions']) != set(DEFAULTS['actions']):
        raise ValueError('Matriz incompleta.')
    if any(v not in ('BLOCK', 'REVIEW', 'ALLOW') for v in config['actions'].values()):
        raise ValueError('Tratamento inválido.')
    for group, fields in [('clients', {'cnh', 'request', 'cpf', 'email', 'phone', 'price'}), ('payments', {'proof', 'identifier'})]:
        if not isinstance(config[group], dict): raise ValueError('Configuração por cadastro inválida.')
        for key, rule in config[group].items():
            if not key or not isinstance(rule, dict) or set(rule) - fields or any(type(v) is not bool for v in rule.values()):
                raise ValueError('Regra por cadastro inválida.')
    erp = config['erp']
    if not isinstance(erp, dict) or set(erp) != set(DEFAULTS['erp']) or type(erp['automatic']) is not bool:
        raise ValueError('Parâmetros ERP inválidos.')
    for key in ('sync_minutes', 'attempts', 'retry_minutes'):
        if type(erp[key]) is not int or not 1 <= erp[key] <= 100000:
            raise ValueError('Intervalos e tentativas ERP devem ser positivos.')
    return copy.deepcopy(config)

def load(con):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='parametros_sistema'").fetchone():
        return copy.deepcopy(DEFAULTS)
    row = con.execute('SELECT config_json FROM parametros_sistema ORDER BY id DESC LIMIT 1').fetchone()
    return validate(json.loads(row[0])) if row else copy.deepcopy(DEFAULTS)

def save(con, config, operator):
    config = validate(config)
    con.execute('CREATE TABLE IF NOT EXISTS parametros_sistema (id INTEGER PRIMARY KEY, config_json TEXT NOT NULL, operador TEXT NOT NULL, salvo_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    con.execute('INSERT INTO parametros_sistema(config_json,operador) VALUES(?,?)', (json.dumps(config, ensure_ascii=False), operator))
    return config

def reference(item, client, catalog):
    sid = str(item.get('servico_erp_id') or '')
    service = next((s for s in catalog['services'] if (sid and (sid in (str(s.get('id_interno') or ''),str(s.get('erp_id') or '')) or s.get('code') == sid)) or (not sid and s.get('name') == item.get('servico'))), None)
    if not service: raise ValueError('Serviço fora do catálogo.')
    price = catalog['prices'].get(service['code'], {})
    if 'by_table_cents' in price:
        from precos_erp import detail
        return detail(price,client)['cents']
    index = int(client.get('price_index') or 0)
    standard = price.get('standard') or 0
    tables = price.get('tables') or []
    specific = tables[index-1] if index > 0 and index <= len(tables) else 0
    particular = client.get('type') == 'PARTICULAR' or str(client.get('name', '')).strip().lower() == 'particular'
    return round(float(standard if particular else specific or standard) * 100)

def method_matches(key, condition):
    read = normalize(condition)
    return bool(read) and read in {
        'PIX': {'PIX'}, 'DEBITO': {'CARTAODEBITO', 'DEBITO'},
        'CREDITO_1X': {'CARTAOCREDITO', 'CARTAOCREDITO1X', 'CREDITO1X'},
        'CREDITO_2X': {'CARTAOCREDITO', 'CARTAOCREDITO2X', 'CREDITO2X'},
    }.get(key, {normalize(key)})

def date(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        # O OCR retorna hora local brasileira sem offset.
        if parsed.tzinfo is None:
            from datetime import timedelta
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=-3)))
        return parsed
    except (ValueError, TypeError): return None

def evaluate(payload, config, con=None, exclude_id=None, catalog=None, enforce=True):
    """Calcula a partir dos dados; nunca confia nos checks enviados pelo navegador."""
    errors, reviews = [], []
    rule = config['clients'].get(str(payload.get('cliente_id') or ''), {})
    docs = payload.get('documentos') or payload.get('documentos_arquivos') or {}
    if config.get('require_crlv',False) and not docs.get('CRLV'): errors.append('Anexe o CRLV obrigatório em todas as vistorias.')
    if rule.get('cnh') and not docs.get('CNH'): errors.append('Anexe a CNH obrigatória para este cliente.')
    if rule.get('request') and not docs.get('REQUISICAO'): errors.append('Anexe a requisição de vistoria emitida pelo cliente.')
    if rule.get('phone') and not re.sub(r'\D', '', str(payload.get('celular') or '')): errors.append('Telefone obrigatório para este cliente.')
    if rule.get('cpf') and len(re.sub(r'\D', '', str(payload.get('cpf') or ''))) != 11: errors.append('CPF obrigatório: informe 11 dígitos.')
    if rule.get('email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', str(payload.get('email') or '')): errors.append('E-mail obrigatório e válido para o cliente.')
    items = payload.get('itens') or []
    if not items: errors.append('Selecione ao menos um serviço.')
    total = sum(int(i.get('preco_cobrado_centavos') or 0) for i in items)
    if any(int(i.get('preco_cobrado_centavos') or 0) < 0 for i in items): errors.append('Preço negativo.')
    if catalog:
        client = next((c for c in catalog['clients'] if c['id_interno'] == payload.get('cliente_id')), None)
        if not client: errors.append('Cliente fora do catálogo.')
        else:
            if not exclude_id and client.get('ativo_erp') is False: errors.append('Cliente inativo no ERP: indisponível para novas OS.')
            if not exclude_id and client.get('periodicidade_pendente'): errors.append('Cliente sem periodicidade válida no ERP. Atualize o cadastro antes de abrir a OS.')
            if not exclude_id:
                from pagamentos_erp import invoice_registration_error
                registration_error=invoice_registration_error(client,catalog.get('paymentConditions',[]))
                if registration_error: errors.append(registration_error)
            for item in items:
                if not exclude_id:
                    sid=str(item.get('servico_erp_id') or '')
                    svc=next((s for s in catalog['services'] if sid in (str(s.get('id_interno') or ''),str(s.get('erp_id') or ''),str(s.get('code') or ''))),None)
                    if svc and svc.get('selecionavel') is False: errors.append('Serviço inativo ou sem vínculo operacional válido no ERP.')
                ref = reference(item, client, catalog)
                if not rule.get('price', False) and int(item.get('preco_cobrado_centavos') or 0) != ref:
                    errors.append('Cliente não permite alteração de preço da tabela.')
                item['preco_referencia_centavos'] = ref
    payload['total_centavos'] = total
    def occurrence(kind, message):
        action = config['actions'][kind]
        if action == 'BLOCK': errors.append(message)
        elif action == 'REVIEW': reviews.append(message)
    if total == 0: occurrence('zero', 'OS com valor zero.')
    mode = payload.get('pagamento_os')
    if mode not in ('A_VISTA', 'FATURADO'): errors.append('Condição da OS inválida.')
    payments = payload.get('pagamentos') or []
    if mode == 'A_VISTA' and not payments and total: errors.append('Informe os pagamentos.')
    if mode == 'FATURADO' and catalog:
        client = next((c for c in catalog['clients'] if c['id_interno'] == payload.get('cliente_id')), {})
        if normalize(client.get('period')) not in ('MENSAL', 'QUINZENAL'): errors.append('Cliente não permite faturamento.')
    seen = set()
    for index, p in enumerate(payments, 1):
        key = p.get('condicao_pagamento')
        if key not in ('PIX','DEBITO','CREDITO_1X','CREDITO_2X','DINHEIRO'): errors.append('Forma de pagamento inválida.')
        pr = payment_rule(config, key)
        proof = p.get('comprovante_imagem') or p.get('comprovante_arquivo')
        reading = p.get('comprovante_leitura') or {}
        if pr['proof'] and not proof: errors.append(f'Pagamento {index}: comprovante obrigatório.')
        identifier = normalize(reading.get('id_transacao') or p.get('identificador_manual'))
        if pr['identifier'] and not identifier: errors.append(f'Pagamento {index}: identificador obrigatório.')
        pair = (key, identifier)
        if identifier and config['block_duplicates']:
            if pair in seen: errors.append('Transação duplicada na OS.')
            seen.add(pair)
            if con:
                rows = con.execute('SELECT os_id,condicao_pagamento,identificador_transacao FROM pagamentos WHERE os_id != ?', (exclude_id or -1,))
                if any(r[1] == key and normalize(r[2]) == identifier for r in rows): errors.append('Transação já utilizada em outra OS, inclusive cancelada.')
                if con.execute("SELECT 1 FROM sqlite_master WHERE name='transacoes_utilizadas'").fetchone():
                    if con.execute('SELECT 1 FROM transacoes_utilizadas WHERE forma=? AND identificador=? AND os_id!=?', (key,identifier,exclude_id or -1)).fetchone():
                        errors.append('Transação já utilizada em outra OS, inclusive cancelada.')
        if key == 'DINHEIRO':
            reviews.append('Pagamento em dinheiro exige revisão administrativa obrigatória.')
            continue
        if not proof and not pr['proof']: continue
        value = reading.get('valor_centavos')
        value_ok = value is not None and abs(int(value)-int(p.get('valor_centavos') or 0)) <= config['tolerance_cents']
        method_ok = method_matches(key, reading.get('condicao'))
        opened, paid = date(payload.get('aberta_em')), date(reading.get('data_hora'))
        time_ok = bool(opened and paid and abs((opened-paid).total_seconds()) <= config['validity_minutes']*60)
        if not value_ok: occurrence('value', f'Pagamento {index}: valor divergente ou não identificado.')
        if not method_ok: occurrence('method', f'Pagamento {index}: forma divergente ou não identificada.')
        if not time_ok: occurrence('time', f'Pagamento {index}: horário fora da validade ou não identificado.')
        reading['validacao'] = {'methodOk': method_ok, 'formOk': method_ok, 'valueOk': value_ok, 'timeOk': time_ok,
            'needsReview': any(not ok and config['actions'][kind] == 'REVIEW' for kind, ok in [('value',value_ok),('method',method_ok),('time',time_ok)])}
    if mode == 'A_VISTA' and abs(sum(int(p.get('valor_centavos') or 0) for p in payments)-total) > config['tolerance_cents']:
        occurrence('value', 'Soma dos pagamentos divergente do total da OS.')
    if mode == 'A_VISTA':
        confirmed=sum(int((p.get('comprovante_leitura') or {}).get('valor_centavos') or 0) if p.get('condicao_pagamento')!='DINHEIRO' and (p.get('comprovante_arquivo') or p.get('comprovante_imagem')) else int(p.get('valor_centavos') or 0) for p in payments)
        if abs(confirmed-total)>config['tolerance_cents']:
            occurrence('value', 'Conciliação financeira dos comprovantes divergente do total da OS.')
    if any(int(p.get('valor_centavos') or 0) < 0 for p in payments): errors.append('Pagamento negativo.')
    if enforce and errors: raise ValueError(' '.join(dict.fromkeys(errors)))
    return {'errors': list(dict.fromkeys(errors)), 'reviews': list(dict.fromkeys(reviews)),
        'status': 'PENDENTE' if errors or reviews else 'LIBERADA_AUTOMATICAMENTE'}

def reserve_transactions(con, payload, os_id):
    """Mantém memória dos identificadores mesmo após substituir pagamentos na edição."""
    con.execute('CREATE TABLE IF NOT EXISTS transacoes_utilizadas(forma TEXT NOT NULL, identificador TEXT NOT NULL, os_id INTEGER NOT NULL, PRIMARY KEY(forma,identificador,os_id))')
    for payment in payload.get('pagamentos', []):
        identifier=normalize((payment.get('comprovante_leitura') or {}).get('id_transacao') or payment.get('identificador_manual'))
        if identifier:
            con.execute('INSERT OR IGNORE INTO transacoes_utilizadas VALUES(?,?,?)',(payment['condicao_pagamento'],identifier,os_id))

def justification_requirements(payload, config, other_changed=False):
    flags=config.get('justifications') or {key:config.get('approval_reason',True) for key in ('proof','financial','other')}
    proofs=[];confirmed=0;unknown=False
    tolerance=config.get('tolerance_cents',0)
    for i,payment in enumerate(payload.get('pagamentos') or [],1):
        cash=payment.get('condicao_pagamento')=='DINHEIRO'
        reading=payment.get('comprovante_leitura') or {}
        attached=payment.get('comprovante_arquivo') or payment.get('comprovante_imagem')
        if cash or (not attached and not payment_rule(config,payment.get('condicao_pagamento'))['proof']):
            confirmed+=int(payment.get('valor_centavos') or 0);continue
        value=reading.get('valor_centavos')
        if value is None: unknown=True
        else: confirmed+=int(value)
        checks=reading.get('validacao') or {}
        bad_value=value is None or abs(int(value)-int(payment.get('valor_centavos') or 0))>tolerance
        bad_method=not method_matches(payment.get('condicao_pagamento'),reading.get('condicao'))
        opened,paid=date(payload.get('aberta_em')),date(reading.get('data_hora'))
        bad_time=not(opened and paid and abs((opened-paid).total_seconds())<=config['validity_minutes']*60)
        if flags['proof'] and any(bad and config['actions'][kind]=='REVIEW' for kind,bad in [('value',bad_value),('method',bad_method),('time',bad_time)]):
            proofs.append(i)
    total=sum(int(i.get('preco_cobrado_centavos') or 0) for i in payload.get('itens') or [])
    financial=bool(flags['financial'] and payload.get('pagamento_os')=='A_VISTA' and (unknown or abs(confirmed-total)>tolerance))
    return {'proofs':proofs,'financial':financial,'other':bool(flags['other'] and other_changed)}

def justification_errors(payload, config, other_changed=False):
    required=justification_requirements(payload,config,other_changed)
    errors=cash_receipt_errors(payload)
    for index in required['proofs']:
        if len(str(payload['pagamentos'][index-1].get('justificativa_divergencia') or '').strip())<10:
            errors.append(f'Pagamento {index}: justificativa por comprovante obrigatória (mínimo 10 caracteres).')
    if required['financial'] and len(str(payload.get('justificativa_financeira') or '').strip())<10:
        errors.append('Justificativa financeira total obrigatória (mínimo 10 caracteres).')
    if required['other'] and len(str(payload.get('justificativa_geral') or '').strip())<10:
        errors.append('Justificativa para outras alterações obrigatória (mínimo 10 caracteres).')
    return errors


def cash_receipt_valid(text, cents):
    """Declaração escrita de recebimento, com valor monetário correspondente."""
    text=str(text or '').strip()
    if len(text)<10 or not re.search(r'\b(recebi|recebemos|recebido|recebida)\b',text,re.I): return False
    amounts=re.findall(r'(?<![\d.,])(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}(?!\d)',text)
    return any(int(amount.replace('.','').replace(',',''))==int(cents) for amount in amounts)


def cash_receipt_errors(payload):
    errors=[]
    for index,payment in enumerate(payload.get('pagamentos') or [],1):
        if payment.get('condicao_pagamento')=='DINHEIRO' and not cash_receipt_valid(payment.get('declaracao_recebimento_dinheiro'),payment.get('valor_centavos') or 0):
            value=f"{int(payment.get('valor_centavos') or 0)/100:.2f}".replace('.',',')
            errors.append(f'Pagamento {index} — dinheiro: declare por escrito o recebimento de R$ {value}. Exemplo: Recebi R$ {value} em dinheiro referente a esta OS.')
    return errors
