"""Rotina diária de Clientes, executável pelo Agendador do Windows."""
import sys
from pathlib import Path
import server

def main():
 if not server.DB_PATH.exists():return 0
 try:server.client_sync().run_daily();return 0
 except Exception:
  print('Atualização diária de Clientes não concluída; base anterior preservada.')
  return 1
if __name__=='__main__':sys.exit(main())
