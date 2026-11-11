/* Cálculo único nas telas do operador e administração; números são os do ERP. */
function erpPriceDetail(price,client){
 if(!price)throw Error('Serviço sem cadastro de preços.');
 const index=Number(client?.price_index??0);
 if(!Number.isInteger(index)||index<0)throw Error('Número de tabela de preços inválido.');
 const particular=client?.type==='PARTICULAR'||String(client?.name||'').trim().toLowerCase()==='particular';
 const requested=particular?0:index;
 let standard,specific;
 if(price.by_table_cents){standard=Number(price.by_table_cents['0']??0);specific=Number(price.by_table_cents[String(requested)]??0)}
 else{standard=Math.round(Number(price.standard||0)*100);specific=requested>0?Math.round(Number(price.tables?.[requested-1]||0)*100):0}
 if(!Number.isSafeInteger(standard)||!Number.isSafeInteger(specific)||standard<0||specific<0)throw Error('Preço inválido no cadastro local.');
 const applied=requested>0&&specific>0?requested:0,value=applied?specific:standard,fallback=requested>0&&!applied;
 return {cents:value,source:applied?'TABELA_CLIENTE':fallback?'TABELA_PADRAO_FALLBACK':'TABELA_PADRAO',table_requested:requested,table_applied:applied,fallback,label:applied?'Tabela '+applied:fallback?'Tabela Padrão (alternativa à Tabela '+requested+')':'Tabela Padrão',variant_erp_id:price.variant_erp_id||null,service_erp_id:price.service_erp_id||null,ultima_atualizacao:price.ultima_atualizacao||null};
}
