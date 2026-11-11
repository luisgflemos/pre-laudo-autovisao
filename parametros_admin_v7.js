/* Editor persistente: todos os valores são validados novamente no servidor. */
let parameterConfig=null;
let savedParameterConfig=null;
let renderCustomizedClients=()=>{};
let parameterLoadId=0;
let parameterSaving=false;
function parameterFeedback(message,kind='info'){
 const status=document.getElementById('parameterStatus');status.textContent=message;status.dataset.kind=kind;
}
function parameterDirty(){if(parameterConfig&&!parameterSaving)parameterFeedback('Alterações não salvas','pending')}
function parameterPayload(config){
 if(!config)throw Error('Carregue as configurações antes de salvar.');
 // Envia somente os campos do contrato; metadados da resposta não são parâmetros.
 const keys=['clients','payments','validity_minutes','require_crlv','tolerance_cents','block_duplicates','cash_review','approval_reason','justifications','actions','erp'];
 const result={};
 for(const key of keys){
  if(config[key]===undefined)throw Error('Configuração incompleta: '+key+'. Recarregue a tela antes de salvar.');
  result[key]=config[key];
 }
 return JSON.parse(JSON.stringify(result));
}
function parameterNode(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e}
function parameterInput(parent,label,value,update,type='checkbox'){
  const row=parameterNode('label');row.className='param-control '+(type==='checkbox'?'param-toggle':'param-number');
  row.append(parameterNode('span',label));const input=parameterNode('input');input.type=type;
  if(type==='checkbox')input.checked=value;else{input.value=value;input.min='0';input.step='1';input.required=true;input.style.width='130px'}
  input.oninput=()=>{update(type==='checkbox'?input.checked:Number(input.value));parameterDirty()};
  input.onchange=input.oninput;row.append(input);parent.append(row);return input;
}
async function loadParameters(){
 if(parameterSaving)return;
 const loadId=++parameterLoadId;
 const status=document.getElementById('parameterStatus');parameterFeedback('Carregando configurações...');
 try{
  const data=await fetchJSON('/api/admin/parametros');
  const catalog=await fetchJSON('/api/admin/catalogo');
  catalog.clients=catalog.clients.filter(c=>c.ativo_erp!==false);
  if(loadId!==parameterLoadId)return;
  parameterConfig=data.config;
  savedParameterConfig=JSON.parse(JSON.stringify(data.config));
  const mount=document.getElementById('parameterFields');mount.replaceChildren();
  function block(title){const a=parameterNode('article');a.className='param-card';a.append(parameterNode('h3',title));mount.append(a);return a}
  const docs=block('1. Obrigações documentais e permissão de preço por cliente');
  const globalBox=parameterNode('div');globalBox.className='param-global';docs.append(globalBox);
  globalBox.append(parameterNode('span','REGRA GLOBAL'));
  parameterInput(globalBox,'Exigir CRLV em todas as vistorias',parameterConfig.require_crlv??true,v=>parameterConfig.require_crlv=v);
  globalBox.append(parameterNode('small','Certificado de Registro e Licenciamento do Veículo. Válido para todos os clientes.'));
  const clientBox=parameterNode('div');clientBox.className='param-client-box';docs.append(clientBox);
  clientBox.append(parameterNode('h4','Configurar cliente'));
  const picker=parameterNode('div');picker.className='param-picker';clientBox.append(picker);
  const search=parameterNode('input');search.placeholder='Buscar nome fantasia ou razão social';search.setAttribute('aria-label','Buscar cliente');picker.append(search);
  const select=parameterNode('select');select.setAttribute('aria-label','Cliente selecionado');picker.append(select);
  const selectedName=parameterNode('div');selectedName.className='param-selected-name';clientBox.append(selectedName);
  const detail=parameterNode('div');detail.className='param-client-options';clientBox.append(detail);
  const help=parameterNode('details');help.className='param-help';help.append(parameterNode('summary','O que estas opções exigem?'),parameterNode('p','CNH: Carteira Nacional de Habilitação. Requisição: solicitação de vistoria emitida pelo cliente. Documentos e dados obrigatórios ausentes bloqueiam o envio. O preço permanece bloqueado sem permissão explícita.'));clientBox.append(help);
  function showClient(){detail.replaceChildren();const id=select.value;
   const selected=catalog.clients.find(c=>c.id_interno===id);selectedName.textContent=selected?(selected.fantasy||selected.name)+' · '+id:'Nenhum cliente encontrado';if(!id)return;
   const rule=parameterConfig.clients[id]||{};
   for(const [key,label] of [['cnh','Exigir CNH — Carteira Nacional de Habilitação'],['request','Exigir anexação da requisição de vistoria emitida pelo cliente'],['cpf','CPF obrigatório'],['email','E-mail obrigatório'],['phone','Telefone obrigatório'],['price','Permitir ao operador alterar preço da tabela']])
    parameterInput(detail,label,rule[key]??false,v=>{parameterConfig.clients[id]={...parameterConfig.clients[id],[key]:v}});
  }
  function filter(){const query=search.value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();select.replaceChildren();
   for(const c of catalog.clients.filter(c=>(String(c.fantasy||'')+' '+c.name).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query)))
    select.add(new Option((c.fantasy||c.name)+' — '+c.name+' ['+c.id_interno+']',c.id_interno));showClient();}
  search.oninput=filter;select.onchange=showClient;filter();
  const gridBox=parameterNode('div');gridBox.className='param-saved-clients';docs.append(gridBox);
  const gridTitle=parameterNode('h4','Clientes com parametrizações personalizadas');gridBox.append(gridTitle);
  gridBox.append(parameterNode('p','Configurações salvas diferentes do padrão. Todas as opções individuais são desabilitadas por padrão.'));
  const grid=parameterNode('div');grid.className='user-table-wrap';gridBox.append(grid);
  renderCustomizedClients=()=>{
   grid.replaceChildren();const table=parameterNode('table');table.className='user-table';
   const head=parameterNode('thead'),headRow=parameterNode('tr');headRow.append(parameterNode('th','Cliente'),parameterNode('th','Ação'));head.append(headRow);table.append(head);
   const body=parameterNode('tbody');table.append(body);
   const fields=['cnh','request','cpf','email','phone','price'];
   const clients=catalog.clients.filter(c=>fields.some(k=>savedParameterConfig.clients[c.id_interno]?.[k]===true)).sort((a,b)=>a.name.localeCompare(b.name,'pt-BR',{sensitivity:'base'}));
   gridTitle.textContent='Clientes com parametrizações personalizadas ('+clients.length+')';
   for(const client of clients){
    const row=parameterNode('tr');row.dataset.clientId=client.id_interno;row.append(parameterNode('td',client.name));
    const action=parameterNode('td'),button=parameterNode('button','Editar');button.type='button';button.className='btn';
    button.onclick=()=>{
     const unsaved=JSON.stringify(parameterConfig.clients[client.id_interno]||{})!==JSON.stringify(savedParameterConfig.clients[client.id_interno]||{});
     if(unsaved&&!confirm('Carregar a configuração salva deste cliente? As alterações não salvas dele serão descartadas.'))return;
     parameterConfig.clients[client.id_interno]=JSON.parse(JSON.stringify(savedParameterConfig.clients[client.id_interno]||{}));
     search.value='';filter();select.value=client.id_interno;showClient();detail.scrollIntoView({behavior:'smooth',block:'center'});
    };
    action.append(button);row.append(action);body.append(row);
   }
   if(!clients.length){const row=parameterNode('tr'),cell=parameterNode('td','Nenhum cliente com parametrização personalizada salva.');cell.colSpan=2;row.append(cell);body.append(row)}
   grid.append(table);
  };
  renderCustomizedClients();
  const payments=block('2. Validação de pagamentos');
  for(const [key,label] of [['PIX','PIX'],['DEBITO','Cartão Débito'],['CREDITO_1X','Cartão Crédito 1X'],['CREDITO_2X','Cartão Crédito 2X']]){
   const paymentCard=parameterNode('div');paymentCard.className='param-payment';paymentCard.append(parameterNode('h4',label));payments.append(paymentCard);
   for(const [field,title] of [['proof','Comprovante obrigatório'],['identifier','Identificador obrigatório']])
    parameterInput(paymentCard,title,parameterConfig.payments[key]?.[field]??(key!=='DINHEIRO'),v=>{parameterConfig.payments[key]={...parameterConfig.payments[key],[field]:v}});
  }
  const validation=payments;validation.append(parameterNode('h4','Validações gerais'));
  parameterInput(validation,'Janela do comprovante em minutos, antes ou depois da abertura da OS',parameterConfig.validity_minutes,v=>parameterConfig.validity_minutes=v,'number');
  const money=parameterInput(validation,'Tolerância monetária (R$)',(parameterConfig.tolerance_cents/100).toFixed(2),v=>parameterConfig.tolerance_cents=Math.round(v*100),'number');money.step='0.01';
  parameterInput(validation,'Bloquear transação duplicada (mesma forma + identificador, incluindo OS canceladas)',parameterConfig.block_duplicates,v=>parameterConfig.block_duplicates=v);
  parameterConfig.cash_review=true;parameterConfig.payments.DINHEIRO={proof:false,identifier:false};
  const cashNote=parameterNode('div');cashNote.className='param-erp-note';cashNote.append(parameterNode('strong','Dinheiro — revisão administrativa obrigatória'),parameterNode('p','Não exige comprovante bancário nem identificador de transação. O recebimento deve ser declarado por escrito e conferido pela administração.'));validation.append(cashNote);
  const matrix=block('3. Regras de operação — tratamento de ocorrências');
  for(const [key,label] of [['value','Divergência de valor'],['time','Comprovante fora da validade'],['method','Divergência de forma de pagamento'],['zero','OS com valor zero']]){
   const row=parameterNode('label');row.className='param-control param-treatment';row.append(parameterNode('span',label));
   const field=parameterNode('select');for(const [value,text] of [['BLOCK','Bloquear envio'],['REVIEW','Revisão administrativa'],['ALLOW','Liberar']])field.add(new Option(text,value));
   field.value=parameterConfig.actions[key];field.dataset.action=field.value;field.onchange=()=>{parameterConfig.actions[key]=field.value;field.dataset.action=field.value;parameterDirty()};row.append(field);matrix.append(row);
  }
  const approval=block('4. Conferência administrativa');
  approval.append(parameterNode('p','Exija justificativas somente para a ocorrência correspondente. Mínimo de 10 caracteres quando obrigatória.'));
  const reasonLabels=[['proof','Justificativa por comprovante','Ao aceitar divergência de valor, forma ou validade de um comprovante.'],['financial','Justificativa financeira total','Quando o total conciliado dos pagamentos não fecha com o total da OS.'],['other','Justificativa para outras alterações','Ao modificar dados, documentos ou serviços, independentemente das divergências dos comprovantes.']];
  for(const [key,label,help] of reasonLabels){const group=parameterNode('div');group.className='param-reason-group';parameterInput(group,label,parameterConfig.justifications[key],v=>parameterConfig.justifications[key]=v);group.append(parameterNode('small',help));approval.append(group)}
  const erp=block('5. Integração ERP');erp.classList.add('param-erp');
  const note=parameterNode('div');note.className='param-erp-note';note.append(parameterNode('strong','Integração ERP'),parameterNode('p','Clientes são atualizados às 03:00 e produtos/serviços às 03:10, diariamente, com atualização manual na tela Integração ERP. As opções abaixo permanecem reservadas ao futuro envio de OS; não geram chamadas adicionais desses cadastros.'));erp.append(note);
  parameterInput(erp,'Integração automática de OS (futura)',parameterConfig.erp.automatic,v=>parameterConfig.erp.automatic=v);
  const schedules=parameterNode('div');schedules.className='param-erp-grid';erp.append(schedules);
  for(const [key,label] of [['sync_minutes','Sincronizar a cada (minutos)'],['attempts','Máximo de tentativas'],['retry_minutes','Reenviar após (minutos)']]){
   const field=parameterInput(schedules,label,parameterConfig.erp[key],v=>parameterConfig.erp[key]=v,'number');field.min='1';
  }
  document.getElementById('parameterForm').hidden=false;parameterFeedback('Configurações carregadas.');
 }catch(e){parameterFeedback('Falha ao carregar: '+e.message,'error');}
}
document.getElementById('parameterForm').onsubmit=async e=>{
 e.preventDefault();if(parameterSaving)return;
 const button=document.getElementById('saveParameters');const form=document.getElementById('parameterForm');
 if(!form.reportValidity())return;
 parameterSaving=true;++parameterLoadId;
 const controls=[...form.querySelectorAll('input,select,button')];controls.forEach(el=>el.disabled=true);
 button.textContent='Salvando...';parameterFeedback('Gravando e conferindo no servidor...');
 try{
  const draft=parameterPayload(parameterConfig);
  const health=await fetchJSON('/api/health');
  if(health.parametros_schema!==3)throw Error('O servidor em execução está desatualizado. Encerre as instâncias antigas e execute INICIAR.bat nesta pasta. Suas alterações permanecem na tela.');
  await fetchJSON('/api/admin/parametros',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config:draft})});
  const stored=await fetchJSON('/api/admin/parametros');
  if(JSON.stringify(stored.config.clients)!==JSON.stringify(draft.clients))throw Error('A conferência da gravação não retornou os clientes enviados. Recarregue as configurações para verificar.');
  parameterConfig=stored.config;savedParameterConfig=JSON.parse(JSON.stringify(stored.config));renderCustomizedClients();
  parameterFeedback('Salvo e conferido no servidor. Grade atualizada.','success');
 }catch(error){parameterFeedback('Não foi possível confirmar a gravação: '+error.message,'error');}
 finally{controls.forEach(el=>el.disabled=false);button.textContent='Salvar parametrizações';parameterSaving=false;}
};
document.getElementById('parameterForm').addEventListener('invalid',e=>{
 parameterFeedback('Revise o campo destacado: '+(e.target.closest('label')?.querySelector('span')?.textContent||e.target.validationMessage),'error');
},true);
document.querySelector('[data-page="Parametrizações"]').addEventListener('click',()=>{
 if(adminToken)loadParameters();
});
