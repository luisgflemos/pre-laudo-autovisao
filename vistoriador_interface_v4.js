/* Interface do operador: obrigatoriedade guiada pelos mesmos parâmetros da API. */
const operatorFields={q:'Cliente',driver:'Nome do condutor',cpf:'CPF',email:'E-mail',phone:'Telefone',plate:'Placa',brandModel:'Marca / Modelo',clientos:'Número da requisição'};
function operatorClientRules(){return systemConfig?.clients[client?.id_interno]||{}}
function operatorFile(kind){const ids={CNH:['cnhfile','cnhcam'],CRLV:['crlvfile','crlvcam'],REQUISICAO:['osfile','oscam']}[kind]||[];return ids.some(id=>document.getElementById(id)?.files?.length)}
function refreshOperatorRequirements(){
 const actionStatus=document.getElementById('operatorActionStatus');if(actionStatus)actionStatus.hidden=step!==4||!cash();
 const rule=operatorClientRules();
 const required={q:true,driver:true,cpf:!!rule.cpf,email:!!rule.email,phone:!!rule.phone,plate:true,brandModel:true,clientos:false};
 for(const [id,label] of Object.entries(operatorFields)){
  const field=document.getElementById(id),title=document.querySelector('label[data-operator-field="'+id+'"]');
  if(field){field.setAttribute('aria-required',String(required[id]));if(!required[id]){field.classList.remove('operator-invalid');field.removeAttribute('aria-invalid')}}
  if(title){title.replaceChildren(document.createTextNode(label));const badge=document.createElement('span');badge.className=required[id]?'required-mark':'optional-mark';badge.textContent=required[id]?' *':' Opcional';title.append(badge)}
 }
 for(const [id,title,needed] of [['cnhDocumentTitle','CNH',!!rule.cnh],['crlvDocumentTitle','CRLV',!!systemConfig?.require_crlv],['requestDocumentTitle','Requisição do cliente',!!rule.request]]){
  const el=document.getElementById(id);if(!el)continue;el.replaceChildren(document.createTextNode(title));
  const badge=document.createElement('span');badge.className='document-status '+(needed?'is-required':'is-optional');badge.textContent=needed?'Obrigatório':'Opcional';el.append(badge);
  if(!needed){const card=el.closest('.document-card');card?.classList.remove('operator-invalid');card?.removeAttribute('aria-invalid')}
  el.closest('.document-card')?.querySelectorAll('label:has(input[type="file"])').forEach(label=>{
   const input=label.querySelector('input[type="file"]');label.setAttribute('role','button');label.tabIndex=0;
   label.setAttribute('aria-label',(input.hasAttribute('capture')?'Tirar foto de ':'Anexar ')+title);
   if(!label.dataset.keyboardReady){label.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();input.click()}});label.dataset.keyboardReady='true'}
  });
 }
 document.querySelectorAll('[data-progress-step]').forEach(el=>{const n=Number(el.dataset.progressStep);el.classList.toggle('is-current',n===step);el.classList.toggle('is-done',n<step);if(n===step)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current')});
}
function operatorStepIssues(number){
 const issues=[],rule=operatorClientRules();
 const missing=(label,id)=>issues.push({label,id,step:number});
 const value=id=>document.getElementById(id)?.value?.trim()||'';
 if(!systemConfig){missing('Configurações não carregadas. Entre novamente para continuar.','q');return issues}
 if(number===1){
  if(!client)missing('Selecione o cliente na lista de resultados.','q');
  if(client&&['MENSAL','QUINZENAL'].includes(String(client.period||'').toUpperCase())&&Array.isArray(client.condicoes_pagamento_erp)){
   const invoices=new Set(D.paymentConditions.filter(p=>p.faturado&&p.selecionavel!==false).map(p=>String(p.Id_CondPgtoERP)));
   if(!client.condicoes_pagamento_erp.some(p=>invoices.has(String(p.erp_id))))missing('Cliente '+clientDisplayName(client)+' ('+client.id_interno+'): periodicidade '+client.period+' sem condição de pagamento Faturado vinculada no ERP. Solicite à administração o cadastro/vínculo da condição no ERP e a atualização de Clientes na aplicação. A OS não pode avançar até a correção.','q');
  }
  if(!value('driver'))missing('Nome do condutor','driver');
  if(rule.cnh&&!operatorFile('CNH'))missing('Anexe a CNH exigida para este cliente.','cnhDocumentCard');
  if(rule.cpf&&!value('cpf'))missing('CPF','cpf');
  else if(rule.cpf&&value('cpf').replace(/\D/g,'').length!==11)missing('CPF: informe os 11 dígitos.','cpf');
  if(rule.email&&!value('email'))missing('E-mail','email');
  else if(rule.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value('email')))missing('E-mail: informe um endereço válido.','email');
  if(rule.phone&&!value('phone').replace(/\D/g,''))missing('Telefone','phone');
 }
 if(number===2){
  if(systemConfig.require_crlv&&!operatorFile('CRLV'))missing('Anexe o CRLV obrigatório.','crlvDocumentCard');
  if(!value('plate'))missing('Placa','plate');
  if(!brand||!model)missing('Marca / Modelo: preencha os dois dados, separados por /.','brandModel');
 }
 if(number===3){
  if(!selected.length)missing('Selecione pelo menos um serviço.','serviceq');
  if(rule.request&&!operatorFile('REQUISICAO'))missing('Anexe a requisição de vistoria emitida pelo cliente.','requestDocumentCard');
 }
 if(number===4&&cash()){
  const total=totalCents();
  if(total===0&&systemConfig.actions.zero==='BLOCK')missing('O total da OS está zerado e o envio está bloqueado pela parametrização.','prices');
  if(document.querySelectorAll('#pricerows .price').length!==selected.length)missing('Confira os valores dos serviços.','prices');
  document.querySelectorAll('#pricerows .price').forEach(el=>{if(el.type!=='hidden'&&!el.value.trim())missing('Informe o preço a cobrar do serviço '+(selected.find(s=>s.code===el.dataset.code)?.name||el.dataset.code)+'.','prices')});
  const payments=paymentParts.filter(p=>p.key||Number(p.value)>0);
  if(total>0&&!payments.length){missing('Pagamento 1: selecione a forma de pagamento.','paymentParts');missing('Pagamento 1: informe o valor.','paymentParts')}
  for(const [index,p] of payments.entries()){
   const label='Pagamento '+(index+1);
   if(!p.key)missing(label+': selecione a forma de pagamento.','paymentParts');
   if(total>0&&!(Number(p.value)>0))missing(label+': informe o valor.','paymentParts');
   if(paymentNeedsProof(p)&&!p.proofAttached)missing(label+': anexe o comprovante obrigatório.','paymentParts');
   if(p.proofReading)missing(label+': aguarde a leitura do comprovante.','paymentParts');
   if(p.key!=='DINHEIRO'&&(systemConfig.payments[p.key]?.identifier??(!!p.key&&p.key!=='DINHEIRO'))&&!String(p.proofRead?.transactionId||p.manualIdentifier||'').trim())missing(label+': identificador da transação não informado ou não identificado.','paymentParts');
  }
  if(total>0&&Math.abs(paymentPartsTotal()-total)>systemConfig.tolerance_cents&&systemConfig.actions.value==='BLOCK')missing('A soma dos pagamentos não fecha com o total da OS.','paymentDistribution');
 }
 return issues;
}
function showOperatorIssues(issues){
 document.getElementById('operatorValidation')?.remove();
 const dialog=document.createElement('dialog');dialog.id='operatorValidation';dialog.className='operator-validation';dialog.setAttribute('aria-labelledby','operatorValidationTitle');
 const kicker=document.createElement('span');kicker.className='dialog-kicker';kicker.textContent='REVISÃO DO PREENCHIMENTO';
 const title=document.createElement('h2');title.id='operatorValidationTitle';title.textContent=issues.length===1?'Revise esta pendência':'Revise estas '+issues.length+' pendências';
 const help=document.createElement('p');help.textContent='Confira os itens abaixo para continuar. Os campos opcionais podem permanecer em branco.';
 const list=document.createElement('ul');
 for(const issue of issues){const li=document.createElement('li');li.textContent=issue.label;list.append(li);const field=document.getElementById(issue.id);if(field){field.classList.add('operator-invalid');field.setAttribute('aria-invalid','true')}}
 const close=document.createElement('button');close.type='button';close.className='primary';close.textContent='Revisar campos';close.onclick=()=>dialog.close();
 dialog.append(kicker,title,help,list,close);document.body.append(dialog);
 dialog.addEventListener('close',()=>{const first=issues[0];dialog.remove();if(first?.step&&step!==first.step){step=first.step;render()}const field=document.getElementById(first?.id);if(field){if(!field.matches('input,select,button'))field.tabIndex=-1;field.scrollIntoView({behavior:'smooth',block:'center'});field.focus({preventScroll:true})}},{once:true});
 dialog.showModal();close.focus();
}
function showOperatorNotice(message){
 document.getElementById('operatorNotice')?.remove();
 const dialog=document.createElement('dialog');dialog.id='operatorNotice';dialog.className='operator-validation';dialog.setAttribute('aria-labelledby','operatorNoticeTitle');
 const title=document.createElement('h2');title.id='operatorNoticeTitle';title.textContent=String(message).includes('gravada')?'OS registrada':'Aviso';
 const text=document.createElement('p');text.textContent=String(message).replace(/^[✓⚠\s]+/,'');
 const button=document.createElement('button');button.className='primary';button.type='button';button.textContent='Entendi';button.onclick=()=>dialog.close();
 dialog.append(title,text,button);document.body.append(dialog);dialog.addEventListener('close',()=>{dialog.remove();document.querySelector('#home:not(.hidden) #new')?.focus()},{once:true});dialog.showModal();button.focus();
}
function refreshOperatorSummary(){
 if(step!==4||!client)return;
 const container=document.getElementById('summary'),wasOpen=!!container.querySelector('details')?.open;container.replaceChildren();
 const details=document.createElement('details');details.open=wasOpen;const heading=document.createElement('summary');heading.textContent='Dados da OS e serviços · '+clientDisplayName(client);
 const root=document.createElement('div');root.className='summary-body';details.append(heading,root);container.append(details);
 const grid=document.createElement('dl');grid.className='operator-summary-grid';
 const payment=cash()?'À vista · pagamento no ato':'Faturado · '+client.period;
 for(const [label,value] of [['Cliente',clientDisplayName(client)],['Pagamento',payment],['Placa',document.getElementById('plate').value],['Veículo',[brand,model].filter(Boolean).join(' ')],['Local da vistoria',loc]]){
  const group=document.createElement('div'),term=document.createElement('dt'),detail=document.createElement('dd');term.textContent=label;detail.textContent=value;group.append(term,detail);grid.append(group);
 }
 root.append(grid);
 const label=document.createElement('h3');label.textContent='Serviços selecionados';const list=document.createElement('ul');
 for(const service of selected){const row=document.createElement('li');row.textContent=service.name;list.append(row)}root.append(label,list);
}
function linkOperatorPaymentLabels(){
 document.querySelectorAll('#paymentParts .pay-form,#paymentParts .pay-value-input').forEach(input=>{input.id=(input.matches('select')?'payment-method-':'payment-value-')+input.dataset.payId;const label=input.parentElement.querySelector('label');if(label)label.htmlFor=input.id});
}
const originalOperatorRender=render;
render=function(){originalOperatorRender();refreshOperatorRequirements();refreshOperatorSummary()};
const originalOperatorMode=setPaymentMode;
setPaymentMode=function(...args){originalOperatorMode(...args);refreshOperatorSummary();if(!cash()){const status=document.getElementById('operatorActionStatus');if(status)status.hidden=true}};
const originalOperatorPayments=renderPaymentParts;
renderPaymentParts=function(){originalOperatorPayments();linkOperatorPaymentLabels();refreshOperatorSummary()};
const originalOperatorDistribution=renderPaymentDistribution;
renderPaymentDistribution=function(){originalOperatorDistribution();refreshOperatorSummary()};
const originalOperatorConfig=loadSystemConfig;
loadSystemConfig=async function(){await originalOperatorConfig();refreshOperatorRequirements()};
valid=function(){return operatorStepIssues(step).length===0};
const originalOperatorNext=document.getElementById('next').onclick;
document.getElementById('next').onclick=async function(){
 if(this.disabled)return;
 try{
  if(step===1||step===4){await loadSystemConfig();if(client)client=D.clients.find(c=>c.id_interno===client.id_interno)||client;}
  const issues=step===4?[1,2,3,4].flatMap(operatorStepIssues):operatorStepIssues(step);
  if(issues.length){document.getElementById('msg').textContent='';showOperatorIssues(issues);return}
  await originalOperatorNext();
  const message=document.getElementById('msg').textContent;
  if(message.startsWith('Não foi possível enviar'))showOperatorIssues([{label:message,id:'next',step:4}]);
 }catch(error){showOperatorIssues([{label:error.message||'Falha ao verificar os parâmetros.',id:'next',step}])}
};
document.getElementById('results').addEventListener('click',()=>refreshOperatorRequirements());
document.getElementById('flow').addEventListener('input',event=>{event.target.classList.remove('operator-invalid');event.target.removeAttribute('aria-invalid')});
document.getElementById('flow').addEventListener('change',event=>{event.target.closest('.document-card')?.classList.remove('operator-invalid');refreshOperatorRequirements()});
refreshOperatorRequirements();

function operatorFinancialState(total,parts,config){
 let declared=0,identified=0,pending=0,waived=0;
 for(const part of parts){
  const value=Number(part.value)||0;declared+=value;
  if(!part.key){if(value)pending++;continue}
  if(part.key==='DINHEIRO'){identified+=value;continue}
  const reading=part.proofRead?.valueCents;
  if(part.proofAttached&&reading!==null&&reading!==undefined&&Number.isFinite(Number(reading))){identified+=Number(reading);continue}
  if((config.payments[part.key]?.proof??true)===false&&!part.proofAttached){identified+=value;waived++;continue}
  pending++;
 }
 return {total,declared,identified,pending,waived,declaredDiff:declared-total,evidenceDiff:pending?null:identified-total,tolerance:config.tolerance_cents||0};
}
function renderCompactFinancial(){
 if(step!==4||!cash()||!systemConfig)return;
 const root=document.getElementById('paymentDistribution');if(!root)return;
 const state=operatorFinancialState(totalCents(),paymentParts,systemConfig);
 const money=cents=>(cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 let action=document.getElementById('operatorActionStatus');
 if(!action){action=document.createElement('div');action.id='operatorActionStatus';action.setAttribute('role','status');document.querySelector('#flow .sticky').prepend(action)}
 action.hidden=false;
 const useEvidence=state.evidenceDiff!==null&&Math.abs(state.evidenceDiff)>state.tolerance;
 const difference=useEvidence?state.evidenceDiff:state.declaredDiff;
 if(Math.abs(difference)>state.tolerance){action.dataset.state='difference';action.textContent=(useEvidence?'Conciliação: ':'Distribuição: ')+(difference<0?'FALTAM ':'EXCEDEM ')+money(Math.abs(difference));}
 else if(state.pending){action.dataset.state='pending';action.textContent='Conciliação pendente: '+state.pending+' pagamento(s) sem leitura.';}
 else{action.dataset.state='balanced';action.textContent='Valores fecham · diferença '+money(Math.abs(difference));}
 root.className='card financial-panel';root.setAttribute('aria-live','polite');root.replaceChildren();
 const title=document.createElement('div');title.className='financial-heading';title.textContent='Fechamento financeiro';root.append(title);
 const grid=document.createElement('div');grid.className='financial-grid';
 for(const [label,amount] of [['Total da OS',state.total],['Total informado',state.declared],[state.pending?'Identificado · parcial':'Para conciliação',state.identified]]){
  const cell=document.createElement('div');cell.className='financial-cell';const name=document.createElement('small'),value=document.createElement('strong');name.textContent=label;value.textContent=money(amount);cell.append(name,value);grid.append(cell);
 }
 root.append(grid);
 function balance(label,diff,pending){
  const box=document.createElement('div');box.className='financial-state';const name=document.createElement('span'),value=document.createElement('strong'),detail=document.createElement('p');name.textContent=label;
  if(pending){box.classList.add('is-pending');value.textContent='PENDENTE DE CONFERÊNCIA';detail.textContent=state.pending+' pagamento(s) sem valor identificado. O valor parcial acima não representa o fechamento completo.';}
  else if(Math.abs(diff)>state.tolerance){box.classList.add('is-difference');value.textContent=(diff<0?'FALTAM ':'EXCEDEM ')+money(Math.abs(diff));detail.textContent=label==='Distribuição dos pagamentos'?'O total informado difere do total da OS.':'Os valores dos comprovantes e do dinheiro diferem do total da OS.';}
  else{box.classList.add('is-balanced');value.textContent=diff===0?'VALORES FECHAM':'DIFERENÇA DENTRO DA TOLERÂNCIA';detail.textContent='Diferença: '+money(Math.abs(diff))+(diff?' · Tolerância: '+money(state.tolerance):'');}
  box.append(name,value,detail);root.append(box);
 }
 balance('Distribuição dos pagamentos',state.declaredDiff,false);
 balance('Conciliação por comprovantes e dinheiro',state.evidenceDiff,!!state.pending);
 const footnote=document.createElement('div');footnote.className='financial-footnote';footnote.textContent='Os comprovantes, a forma e o horário continuam sujeitos às validações configuradas.'+(state.waived?' Pagamentos dispensados de comprovante usam o valor informado.':'')+(paymentParts.some(p=>p.key==='DINHEIRO')?' Dinheiro exige revisão administrativa.':'');root.append(footnote);
}
const distributionBeforeCompact=renderPaymentDistribution;
renderPaymentDistribution=function(){distributionBeforeCompact();renderCompactFinancial()};
