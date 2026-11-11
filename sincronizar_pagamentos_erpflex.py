"""Atualização diária somente de leitura das formas de pagamento."""
import sys,server
if __name__=='__main__':
 try:
  if server.DB_PATH.exists():server.payment_sync().run_daily()
 except Exception:
  print('Atualização de pagamentos falhou; última base preservada.');sys.exit(1)
