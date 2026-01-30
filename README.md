# Sistema de Indicadores (Flask + SQL Server)

Aplicação web para gestão de indicadores corporativos por setor e período, com **fluxo de aprovação** e **controle de acesso por perfis (RBAC)**. O backend expõe uma API REST e também serve a interface web pelo próprio Flask.

## Como o sistema funciona
1. **Gestão/ADM** cadastra setores, indicadores e usuários.
2. **Editor** preenche valores mensais por indicador e setor; o sistema grava como **rascunho (draft)**.
3. **Editor** envia o rascunho para aprovação.
4. **Líder** revisa e aprova/rejeita.
5. Quando aprovado, o valor é gravado como **definitivo** e fica disponível para consulta e BI.

## Perfis de acesso (RBAC)
- **1 Leitor**: consulta indicadores e valores oficiais.
- **2 Editor**: cria/edita rascunhos e envia para aprovação.
- **3 Líder**: aprova/rejeita rascunhos e consolida valores.
- **4 Gestão**: tudo anterior + CRUD de indicadores e criação de usuários abaixo do nível.
- **5 ADM**: acesso total.

## Estrutura de dados (SQL Server)
- **ZSE**: setores.
- **ZFU**: usuários/funcionários.
- **ZIN**: indicadores.
- **ZDR**: rascunhos com status (DRAFT/PENDING/APPROVED/REJECTED).
- **ZIV**: valores oficiais/definitivos.
- **VW_PBI_INDICADORES_OFICIAIS**: view para consumo em BI (apenas dados oficiais).

## Requisitos
- **Python 3.10+**
- **SQL Server** + **ODBC Driver 18 for SQL Server**
- **Windows** (exemplos em PowerShell)

## Como rodar localmente (Windows)

1) Criar e ativar o ambiente virtual:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Instalar dependências:
```powershell
pip install -r requirements.txt
```

3) Configurar variáveis de ambiente

O app lê automaticamente o arquivo `.env` na raiz do projeto. Exemplo:

```env
SQL_SERVER=SEU_SERVIDOR
SQL_DATABASE=SEU_BANCO
SQL_USER=SEU_USUARIO
SQL_PASSWORD=SUA_SENHA
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_TRUSTED_CONNECTION=false
SQL_ENCRYPT=yes
SQL_TRUST_CERT=no

JWT_SECRET=uma-chave-grande
JWT_EXPIRES_HOURS=12
SEED_ADMIN_ENABLED=true
SEED_ADMIN_EMAIL=admin@empresa.com
SEED_ADMIN_PASSWORD=defina_uma_senha_forte
```

Se usar Windows Auth:
```env
SQL_TRUSTED_CONNECTION=true
```

4) Criar banco e tabelas:
- Execute `sql/schema.sql` no SQL Server (o script cria o banco **PRD_WEB_APP** por padrão).

5) Rodar o servidor:
```powershell
python run.py
```

Acesse: `http://127.0.0.1:5000/`

## Publicar no DNS local (intranet)

1) **Garantir IP fixo do servidor**
- Defina IP estático ou reserva DHCP para a máquina que vai hospedar o app.

2) **Expor o Flask na rede**
- No `.env`, configure:
```env
APP_HOST=0.0.0.0
APP_PORT=5000
```
- Inicie o servidor com `python run.py`.

3) **Liberar a porta no firewall do Windows**
- Crie uma regra de entrada para a porta `5000` (ou a que você definir):
```powershell
New-NetFirewallRule -DisplayName "Indicadores Flask 5000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
```

4) **Criar registro no DNS interno**
- No servidor DNS (ex.: Windows DNS Manager), crie um **A record**:
  - Nome: `indicadores` (exemplo)
  - IP: `IP_DO_SERVIDOR`
- Resultado esperado: `http://indicadores.seudominio.local:5000/`

5) **Testar**
```powershell
Resolve-DnsName indicadores.seudominio.local
Test-NetConnection indicadores.seudominio.local -Port 5000
```

> Se for usar proxy reverso (IIS/Nginx) e HTTPS, habilite `TRUST_PROXY_HEADERS=true` e `FORCE_HTTPS=true` no `.env`.

## Endpoints principais (API)
- `POST /api/auth/login`
- `GET /api/me`
- `GET /api/setores` | `POST /api/setores`
- `GET /api/indicadores` | `POST /api/indicadores`
- `GET /api/valores?setor_id=1&periodo=YYYY-MM-DD` | `POST /api/valores`
- `POST /api/drafts`
- `POST /api/drafts/submit`
- `POST /api/drafts/approve`
- `POST /api/drafts/{id}/reject`
- `GET /api/drafts?setor_id=1&periodo=YYYY-MM-DD`
- `GET /api/drafts/pending` | `GET /api/drafts/rejected`
- `GET /api/users` | `POST /api/users`

> Consulte `src/app.py` para a lista completa de rotas e regras de permissão.
