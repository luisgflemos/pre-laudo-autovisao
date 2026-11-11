# Pré-Laudo Auto Visão

Código do Pré-Laudo do Vistoriador e da Camada Intermediária. Este pacote contém catálogos vazios. A operação precisa configurar os cadastros e usuários no ambiente de destino.

## Execução local

Instale Python e as dependências de requirements.txt. Copie config.env.example para config.env e configure a chave OpenAI nesse arquivo. Execute INICIAR.bat no Windows ou python server.py para iniciar o servidor local. A aplicação usa a porta 8765.

## Implantação

O servidor atual usa Python HTTPServer, SQLite local e arquivos locais para comprovantes. O acesso ERP salvo localmente usa proteção do Windows. Para hospedar na Vercel e usar Supabase, adaptar as rotas do servidor, persistência em Postgres, armazenamento privado dos comprovantes e configuração de credenciais e sessões. Validar autenticação e fluxos antes de apontar o domínio de produção. A gravação de orçamento por unidade no ERP ainda depende da orientação do fornecedor.

Configurar os segredos no ambiente de hospedagem. A migração de dados deve ocorrer por canal privado, com acesso restrito.
