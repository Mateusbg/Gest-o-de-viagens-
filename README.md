# 📊 Sistema de Indicadores (Flask + SQL Server)

Este projeto foi ajustado para **rodar localmente** (sem Vercel) e já está com **endpoints prontos** para salvar/ler indicadores no **SQL Server**.

## ✅ Como rodar local (Windows)

1) Crie e ative um venv:
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2) Instale dependências:
```bash
pip install -r requirements.txt
```

3) Configure conexão com o SQL Server (PowerShell):
```powershell
$env:SQL_SERVER="SEU_SERVIDOR"      # ex: localhost\SQLEXPRESS
$env:SQL_DATABASE="SEU_BANCO"
$env:SQL_USER="SEU_USUARIO"         # se for login SQL
$env:SQL_PASSWORD="SUA_SENHA"
$env:SQL_DRIVER="ODBC Driver 18 for SQL Server"  # opcional
# ou, se usar Windows Auth:
# $env:SQL_TRUSTED_CONNECTION="true"
```

4) Crie as tabelas no SQL Server:
- Execute o script: `sql/schema.sql`

5) Rode o servidor:
```bash
python app.py
```

Acesse:
- http://127.0.0.1:5000/

## 🔌 Endpoints (backend)

- `GET /api/health` (use `?db=1` para testar o banco)
- `GET /api/setores`
- `GET /api/indicadores?setor_id=1`
- `POST /api/valores` (salvar valores)
- `POST /api/drafts` (salvar rascunhos)
- `GET /api/drafts?setor_id=1&periodo=2026-01`

> Observação: o frontend atual ainda tem regras de login/permite memória local, mas o backend já está pronto para persistir no SQL Server via API.

## 🧹 O que foi removido

- Configurações e pasta de deploy **Vercel** (vercel.json / api handler / runtime).
