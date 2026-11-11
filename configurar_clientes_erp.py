"""Habilita somente a entrada automática de Clientes. Credencial protegida pelo Windows."""
import tkinter as tk,threading,queue
from tkinter import ttk
import clientes_erp,server

def main():
 app=tk.Tk();app.title('Auto Visão — Configurar Clientes ERP');app.geometry('680x490');app.configure(bg='#f4f4f4')
 frame=tk.Frame(app,bg='white',padx=24,pady=20);frame.pack(fill='both',expand=True,padx=16,pady=16)
 tk.Label(frame,text='Integrar Clientes do ERP',font=('Segoe UI',18,'bold'),bg='white').pack(anchor='w')
 tk.Label(frame,text='Atualização diária às 03:00 e botão manual na administração.',bg='white',fg='#637084').pack(anchor='w',pady=(5,12))
 tk.Label(frame,text='Produção · consulta de Clientes\nhttps://api.erpflex.com.br/api/clientes',bg='#f4f7fb',fg='#4b5565',justify='left',padx=10,pady=10).pack(fill='x',pady=6)
 tk.Label(frame,text='Usuário',bg='white').pack(anchor='w');username=tk.StringVar(value='');ttk.Entry(frame,textvariable=username).pack(fill='x',pady=(3,10))
 tk.Label(frame,text='Senha da API',bg='white').pack(anchor='w');secret=tk.StringVar();entry=ttk.Entry(frame,textvariable=secret,show='●');entry.pack(fill='x',pady=(3,10))
 allow=tk.BooleanVar(value=True);tk.Checkbutton(frame,text='Guardar o acesso protegido neste usuário do Windows para a rotina diária.',variable=allow,bg='white',wraplength=570,justify='left').pack(anchor='w',pady=6)
 state=tk.StringVar(value='Ao ativar: consulta atual, importação do cadastro e habilitação do acesso diário.');tk.Label(frame,textvariable=state,bg='white',fg='#4b5565',wraplength=570,justify='left').pack(fill='x',pady=10)
 messages=queue.Queue();busy=False
 def start():
  nonlocal busy
  if busy:return
  user=username.get().strip();password=secret.get()
  if not user or not password:state.set('Informe o usuário e a senha.');entry.focus_set();return
  if not allow.get():state.set('Para a rotina automática, autorize o armazenamento protegido do acesso.');return
  busy=True;button.configure(state='disabled');secret.set('');state.set('Consultando e importando Clientes...')
  def task():
   try:
    result=server.client_sync().synchronize({'username':user,'password':password})
    clientes_erp.save_access(user,password)
    clientes_erp.atomic_json(clientes_erp.ROOT/'work/erpflex_clientes/ativacao.json',{'ok':True,**result,'rotina':'diariamente 03:00 America/Sao_Paulo'})
    messages.put(('done',f"Integração ativada: {result['total_erp']} clientes do ERP; {result['ativos']} disponíveis e {result['inativos']} inativos. Rotina diária às 03:00."))
   except Exception:messages.put(('error','Não foi possível concluir a ativação. Confira usuário, senha e conexão. O acesso não foi gravado.'))
  threading.Thread(target=task,daemon=True).start()
 def poll():
  nonlocal busy
  try:
   while True:
    kind,message=messages.get_nowait();busy=False;button.configure(state='normal');state.set(message)
  except queue.Empty:pass
  app.after(200,poll)
 button=tk.Button(frame,text='Consultar, importar e ativar',command=start,bg='#bf1515',fg='white',font=('Segoe UI',11,'bold'),relief='flat',padx=14,pady=10);button.pack(anchor='e',pady=8)
 app.after(200,poll);entry.focus_set();app.mainloop()
if __name__=='__main__':main()
