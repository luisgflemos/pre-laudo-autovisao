"""Atualização diária de Transportadoras: somente leitura ERP."""
import sys,server
if __name__=='__main__':
 try:
  if server.DB_PATH.exists():server.carrier_sync().run_daily()
 except Exception:
  print('Atualização de vistoriadores falhou; última base preservada.');sys.exit(1)
