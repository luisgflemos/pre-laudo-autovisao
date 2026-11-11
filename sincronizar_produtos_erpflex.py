"""Carga diária somente de leitura dos produtos e serviços do ERPFlex."""
import sys,server
def main():
 if not server.DB_PATH.exists():return 0
 try:server.product_sync().run_daily();return 0
 except Exception:
  print('Atualização de produtos/serviços não concluída; catálogo anterior preservado.');return 1
if __name__=='__main__':sys.exit(main())
