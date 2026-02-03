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
- **SQL Server** + **ODBC Driver 17/18 for SQL Server**
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

## Publicar na intranet (HTTP via IIS)

1) **Rodar o app localmente (Loopback)**
```env
APP_HOST=127.0.0.1
APP_PORT=5000
FORCE_HTTPS=false
TRUST_PROXY_HEADERS=false
```
```powershell
.\.venv\Scripts\python.exe -m waitress --host=127.0.0.1 --port=5000 src.app:app
```

2) **Configurar IIS como proxy reverso**
- Instale **IIS**, **URL Rewrite** e **ARR**.
- Crie um site no IIS apontando para uma pasta com o `web.config` do projeto.
- Binding HTTP na porta 80 para:
  - `web-indicadore.com`
  - `www.web-indicadore.com`
  - `web-indicadore`

3) **Liberar porta 80 no firewall**
```powershell
New-NetFirewallRule -DisplayName "IIS HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80
```

4) **DNS interno**
- A records apontando para o IP do servidor (ex.: `192.168.31.201`).
- Resultado esperado: `http://web-indicadore.com/`

> Para HTTPS, é necessário certificado válido e bindings 443. Caso opte por HTTPS, habilite `TRUST_PROXY_HEADERS=true` e `FORCE_HTTPS=true`.

## Rodar como serviço (NSSM)
```powershell
.\nssm.exe install web-indicadore
```
Configuração:
- **Path**: `...\Gest-o-de-viagens-\.venv\Scripts\python.exe`
- **Arguments**: `-m waitress --host=127.0.0.1 --port=5000 src.app:app`
- **Startup directory**: `...\Gest-o-de-viagens-`

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
