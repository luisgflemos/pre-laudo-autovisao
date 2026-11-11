/* Verificações locais: dados obrigatórios não são enviados antes de completos. */
function localParameterErrors(payload){
 const cfg=systemConfig;
 if(!cfg)return ['Não foi possível carregar os parâmetros.'];
 const errors=[],rule=cfg.clients[payload.cliente_id]||{};
 if(cfg.require_crlv&&!payload.documentos?.CRLV)errors.push('Anexe o CRLV obrigatório em todas as vistorias.');
 if(rule.cnh&&!payload.documentos?.CNH)errors.push('Anexe a CNH obrigatória para este cliente.');
 if(rule.request&&!payload.documentos?.REQUISICAO)errors.push('Anexe a requisição de vistoria emitida pelo cliente.');
 if(rule.phone&&!String(payload.celular||'').replace(/\D/g,''))errors.push('Informe o telefone obrigatório para este cliente.');
 if(rule.cpf&&String(payload.cpf||'').replace(/\D/g,'').length!==11)errors.push('Informe o CPF obrigatório com 11 dígitos.');
 if(rule.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email||''))errors.push('Informe um e-mail válido para este cliente.');
 if(!payload.total_centavos&&cfg.actions.zero==='BLOCK')errors.push('OS com valor zero: envio bloqueado.');
 const seen=new Set();
 for(const p of payload.pagamentos){
  const pr=cfg.payments[p.condicao_pagamento]||{},proofRequired=p.condicao_pagamento!=='DINHEIRO'&&(pr.proof??true);
  const idRequired=p.condicao_pagamento!=='DINHEIRO'&&(pr.identifier??true);
  const reading=p.comprovante_leitura;
  if(proofRequired&&!p.comprovante_imagem)errors.push('Anexe o comprovante obrigatório de '+p.condicao_pagamento+'.');
  const id=String(reading?.id_transacao||p.identificador_manual||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[^A-Z0-9]/g,'');
  if(idRequired&&!id)errors.push('Identificador obrigatório em '+p.condicao_pagamento+'.');
  const pair=p.condicao_pagamento+':'+id;
  if(id&&cfg.block_duplicates&&seen.has(pair))errors.push('Transação duplicada entre pagamentos da OS.');
  seen.add(pair);
  if(p.condicao_pagamento==='DINHEIRO'||(!proofRequired&&!p.comprovante_imagem))continue;
  const part=paymentParts.find(x=>x.key===p.condicao_pagamento&&x.proofDataUrl===p.comprovante_imagem);
  const checks=part?proofValidationFor(part):{formOk:false,valueOk:false,timeOk:false};
  for(const [key,ok,message] of [['method',checks.formOk,'Forma de pagamento divergente.'],['value',checks.valueOk,'Valor do comprovante divergente.'],['time',checks.timeOk,'Comprovante fora da validade.']])
   if(!ok&&cfg.actions[key]==='BLOCK')errors.push(message);
 }
 if(payload.pagamento_os==='A_VISTA'&&Math.abs(payload.pagamentos.reduce((sum,p)=>sum+p.valor_centavos,0)-payload.total_centavos)>cfg.tolerance_cents&&cfg.actions.value==='BLOCK')
  errors.push('Soma dos pagamentos divergente do total.');
 return [...new Set(errors)];
}
