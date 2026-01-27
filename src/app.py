"""
===========================================================
SISTEMA (FLASK) - INDICADORES + RBAC
===========================================================

Autor: Mateus Barbosa
Refactor: (app.py limpo/estruturado)
Data: 22/01/2026

Objetivo:
- Backend Flask com:
  - Login JWT
  - RBAC (níveis 1..5)
  - Setores / Indicadores / Valores (definitivo) / Drafts (rascunhos)
  - Fluxo Editor -> Submit -> Líder aprova -> grava em definitivo
  - Gestão/ADM: CRUD de usuários e indicadores

Níveis:
1 LEITOR  : só vê indicadores/valores
2 EDITOR  : salva drafts e envia para aprovação
3 LIDER   : aprova drafts e salva definitivo
4 GESTAO  : tudo anterior + cria usuários (abaixo do nível) + CRUD indicadores
5 ADM     : tudo (super user)

Variáveis de ambiente (.env) esperadas:
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_SERVER=SEU_SERVIDOR
SQL_DATABASE=SEU_BANCO
SQL_USER=SEU_USUARIO
SQL_PASSWORD=SUA_SENHA
SQL_TRUSTED_CONNECTION=false
SQL_ENCRYPT=yes
SQL_TRUST_CERT=yes

JWT_SECRET=uma-chave-grande
JWT_EXPIRES_HOURS=12

SEED_ADMIN_EMAIL=admin@empresa.com
SEED_ADMIN_PASSWORD=1234
===========================================================
"""

from __future__ import annotations

# =========================
# 0) BOOTSTRAP / ENV
# =========================
from dotenv import load_dotenv
from pathlib import Path
_ROOT = Path(__file__).resolve().parent
_ENV = _ROOT.parent / ".env"
load_dotenv(dotenv_path=_ENV, override=False)

# =========================
# 1) IMPORTS
# =========================
import os
import traceback
from datetime import datetime, timedelta, timezone

import pyodbc
import jwt

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from functools import wraps
from passlib.context import CryptContext

# =========================
# 2) APP / CONFIG
# =========================
app = Flask(__name__)
CORS(app)

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "12"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_MAP = {
    1: "LEITOR",
    2: "EDITOR",
    3: "LIDER",
    4: "GESTAO",
    5: "ADM",
}

# =========================
# 3) DB CONNECTION (SQL Server)
# =========================
def get_db_connection():
    """
    Abre conexão com SQL Server usando variáveis de ambiente padrão SQL_*.
    Suporta:
    - SQL_TRUSTED_CONNECTION=true (Windows Auth)
    - SQL_ENCRYPT / SQL_TRUST_CERT
    """
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER", "")
    database = os.getenv("SQL_DATABASE", "")
    user = os.getenv("SQL_USER", "")
    password = os.getenv("SQL_PASSWORD", "")

    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "false").lower() in ("1", "true", "yes", "y")
    encrypt = os.getenv("SQL_ENCRYPT", "yes").lower() in ("1", "true", "yes", "y")
    trust_cert = os.getenv("SQL_TRUST_CERT", "yes").lower() in ("1", "true", "yes", "y")

    if not server or not database:
        raise RuntimeError("SQL_SERVER e SQL_DATABASE não configurados no .env")

    enc_part = "Encrypt=yes;" if encrypt else "Encrypt=no;"
    trust_part = "TrustServerCertificate=yes;" if trust_cert else "TrustServerCertificate=no;"

    if trusted:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            + enc_part + trust_part
        )
    else:
        if not user or not password:
            raise RuntimeError("SQL_USER e SQL_PASSWORD não configurados no .env")
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};PWD={password};"
            + enc_part + trust_part
        )

    return pyodbc.connect(conn_str)

def _rows_to_dicts(cur, rows):
    """Converte cursor rows em lista de dicts (JSON friendly)."""
    cols = [c[0] for c in cur.description]
    out = []
    for r in rows:
        d = {}
        for i, col in enumerate(cols):
            v = r[i]
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            d[col] = v
        out.append(d)
    return out

# =========================
# 4) AUTH / JWT / RBAC
# =========================
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def _jwt_secret():
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET não configurado no .env")
    return JWT_SECRET

def _issue_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "nivel": int(user["nivel"]),
        "setor_id": int(user["setor_id"]) if user.get("setor_id") is not None else None,
        "nome": user.get("nome"),
        "email": user.get("email"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRES_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

def _decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        _jwt_secret(),
        algorithms=["HS256"],
        options={"require": ["sub", "exp"], "verify_iat": False},
        leeway=120,
    )

def _get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

def get_current_user(optional: bool = False):
    token = _get_bearer_token()
    if not token:
        if optional:
            return None
        raise PermissionError("Token ausente")
    try:
        data = _decode_token(token)
        return {
            "id": int(data["sub"]),
            "nivel": int(data["nivel"]),
            "setor_id": data.get("setor_id"),
            "nome": data.get("nome"),
            "email": data.get("email"),
        }
    except jwt.ExpiredSignatureError as e:
        print(f"[AUTH] token expirado: {e}")
        if optional:
            return None
        raise PermissionError("Token expirado")
    except jwt.InvalidTokenError as e:
        print(f"[AUTH] token inválido: {e}")
        if optional:
            return None
        raise PermissionError("Token inválido")
    except Exception as e:
        print(f"[AUTH] erro ao decodificar token: {e}")
        if optional:
            return None
        raise PermissionError("Token inválido/expirado")

def require_level(min_level: int):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                user = get_current_user(optional=False)
            except PermissionError as e:
                return jsonify({"ok": False, "error": str(e)}), 401

            if int(user["nivel"]) < int(min_level):
                return jsonify({"ok": False, "error": f"Permissão insuficiente (requer nível >= {min_level})"}), 403

            request.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return deco

def _is_gestao_or_admin(user: dict) -> bool:
    return int(user["nivel"]) >= 4

def _enforce_setor_access(user: dict, setor_id: int):
    """Gestão/ADM vê tudo; abaixo disso só acessa o próprio setor."""
    if _is_gestao_or_admin(user):
        return
    if user.get("setor_id") is None:
        raise PermissionError("Usuário sem setor associado")
    if int(user["setor_id"]) != int(setor_id):
        raise PermissionError("Acesso negado a este setor")

def _fetch_user_by_email(cur, email: str):
    cur.execute(
        "SELECT ZFU_ID, ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO "
        "FROM ZFU WHERE LOWER(ZFU_EMAIL) = LOWER(?)",
        (email,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "nome": row[1],
        "email": row[2],
        "setor_id": row[3],
        "nivel": int(row[4] or 1),
        "senha_hash": row[5],
        "ativo": bool(row[6]),
    }

def _fetch_user_by_id(cur, user_id: int):
    cur.execute(
        "SELECT ZFU_ID, ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO "
        "FROM ZFU WHERE ZFU_ID = ?",
        (int(user_id),)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "nome": row[1],
        "email": row[2],
        "setor_id": row[3],
        "nivel": int(row[4] or 1),
        "senha_hash": row[5],
        "ativo": bool(row[6]),
    }


def _get_assigned_sector_ids(cur, user_id: int) -> list[int]:
    cur.execute(
        "SELECT DISTINCT ZIN_SETOR_ID FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_RESPONSAVEL_ID = ?",
        (int(user_id),)
    )
    rows = cur.fetchall()
    return [int(r[0]) for r in rows if r and r[0] is not None]

def _get_indicator_access(cur, indicador_id: int):
    cur.execute(
        "SELECT ZIN_SETOR_ID, ZIN_RESPONSAVEL_ID FROM ZIN WHERE ZIN_ID = ?",
        (int(indicador_id),)
    )
    row = cur.fetchone()
    if not row:
        return None, None
    setor_id = int(row[0]) if row[0] is not None else None
    responsavel_id = int(row[1]) if row[1] is not None else None
    return setor_id, responsavel_id

def _can_user_fill_indicator(user: dict, indicador_setor_id: int, responsavel_id: int | None) -> bool:
    nivel = int(user.get("nivel") or 1)
    user_id = int(user.get("id"))
    user_setor_id = user.get("setor_id")
    if nivel >= 5:
        return True
    if nivel >= 4:
        return True
    if nivel == 3:
        if user_setor_id is not None and int(user_setor_id) == int(indicador_setor_id):
            return responsavel_id is None or int(responsavel_id) == user_id
        return responsavel_id is not None and int(responsavel_id) == user_id
    if nivel == 2:
        if user_setor_id is None:
            return False
        if int(user_setor_id) != int(indicador_setor_id):
            return False
        return responsavel_id is None or int(responsavel_id) == user_id
    return False

def _log_action(user: dict | None, action: str, details: str | None = None):
    who = f"user_id={user.get('id')}" if user else "user_id=none"
    when = datetime.utcnow().isoformat()
    extra = f" details={details}" if details else ""
    print(f"[AUDIT] {when} action={action} {who}{extra}")

def ensure_seed_admin():
    """
    Se não existir nenhum usuário nível 5 ativo, cria um ADM inicial.

    - Usa SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD (do .env).
    - Para compatibilidade com o frontend legado (que muitas vezes tenta "ad"/"1120"),
      também garante o usuário "ad" (nível 5) caso não exista, sem depender do .env.
      (isso evita o "Login inválido" logo no 1º uso).
    """
    seed_email = (os.getenv("SEED_ADMIN_EMAIL") or "admin@empresa.com").strip()
    seed_pass = os.getenv("SEED_ADMIN_PASSWORD") or "1234"

    legacy_email = (os.getenv("SEED_LEGACY_ADMIN_EMAIL") or "").strip()
    legacy_pass = os.getenv("SEED_LEGACY_ADMIN_PASSWORD") or "1120"

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Se já existe algum ADM ativo, não precisamos criar o seed principal,
        # mas ainda podemos garantir o legacy se quiser.
        cur.execute("SELECT COUNT(1) FROM ZFU WHERE ISNULL(ZFU_NIVEL,1) = 5 AND ZFU_ATIVO = 1")
        has_admin = int(cur.fetchone()[0] or 0)

        def _ensure_user(email: str, password: str, nome: str):
            cur.execute("SELECT ZFU_ID FROM ZFU WHERE LOWER(ZFU_EMAIL) = LOWER(?)", (email,))
            row = cur.fetchone()
            if row and row[0]:
                return
            cur.execute(
                "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO, ZFU_CRIADO_EM) "
                "VALUES (?, ?, NULL, 5, ?, 1, SYSUTCDATETIME())",
                (nome, email, hash_password(password))
            )

        if not has_admin:
            _ensure_user(seed_email, seed_pass, "Administrador")

        # Compatibilidade (pode desativar colocando SEED_LEGACY_ADMIN_EMAIL vazio)
        if legacy_email:
            _ensure_user(legacy_email, legacy_pass, "Admin (legacy)")

        conn.commit()

@app.before_request
def _seed_admin_once():
    # tenta seed silencioso
    try:
        ensure_seed_admin()
    except Exception:
        pass

# =========================
# 5) HELPERS DE UPSERT (Setor / Funcionário / Indicador)
# =========================
def _pick(d: dict, *keys, default=None):
    """Pega o primeiro valor não-nulo de um dict (múltiplos aliases)."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return default

def _get_or_create_setor(cur, setor_id, setor_nome):
    if setor_id:
        cur.execute("SELECT ZSE_ID FROM ZSE WHERE ZSE_ID = ?", (int(setor_id),))
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        raise ValueError("Setor informado nao existe")

    nome = (setor_nome or "").strip()
    if not nome:
        raise ValueError("Setor nao informado")

    cur.execute("SELECT ZSE_ID FROM ZSE WHERE LOWER(ZSE_NOME) = LOWER(?)", (nome,))
    row = cur.fetchone()
    if row and row[0]:
        return int(row[0])

    cur.execute("INSERT INTO ZSE (ZSE_NOME, ZSE_ATIVO) VALUES (?, 1)", (nome,))
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])

def _get_or_create_funcionario(cur, funcionario_id, funcionario_email, funcionario_nome, setor_id=None):
    if funcionario_id:
        cur.execute("SELECT ZFU_ID FROM ZFU WHERE ZFU_ID = ?", (int(funcionario_id),))
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        raise ValueError("Funcionario informado nao existe")

    email = (funcionario_email or "").strip()
    nome = (funcionario_nome or "").strip() or email

    if email:
        cur.execute("SELECT ZFU_ID FROM ZFU WHERE LOWER(ZFU_EMAIL) = LOWER(?)", (email,))
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
    else:
        if not nome:
            raise ValueError("Funcionario nao informado")
        cur.execute("SELECT ZFU_ID FROM ZFU WHERE LOWER(ZFU_NOME) = LOWER(?)", (nome,))
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        raise ValueError("Email do funcionario obrigatorio para criar")

    cur.execute(
        "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO, ZFU_CRIADO_EM) "
        "VALUES (?, ?, ?, 1, ?, 1, SYSUTCDATETIME())",
        (nome, email, setor_id, hash_password("1234"))
    )
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])

def _get_or_create_indicador(cur, indicador_id, setor_id, codigo, nome, tipo=None, unidade=None, meta=None):
    if indicador_id:
        cur.execute("SELECT ZIN_ID FROM ZIN WHERE ZIN_ID = ?", (int(indicador_id),))
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        raise ValueError("Indicador informado nao existe")

    if not setor_id or codigo is None:
        raise ValueError("Indicador sem setor ou codigo")

    cur.execute(
        "SELECT ZIN_ID FROM ZIN WHERE ZIN_SETOR_ID = ? AND ZIN_CODIGO = ?",
        (int(setor_id), str(codigo))
    )
    row = cur.fetchone()
    if row and row[0]:
        return int(row[0])

    cur.execute(
        "INSERT INTO ZIN (ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_CRIADO_EM) "
        "VALUES (?, ?, ?, ?, ?, ?, 1, SYSUTCDATETIME())",
        (int(setor_id), str(codigo), str(nome), tipo, unidade, meta)
    )
    cur.execute("SELECT SCOPE_IDENTITY()")
    return int(cur.fetchone()[0])



# ===========================================================
# 6) ROTAS BÁSICAS (UI)
# =========================
@app.route("/")
def index():
    return render_template("index.html")

# =========================
# 7) AUTH ROUTES
# =========================
@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """
    Login via email/senha.
    Retorna token JWT + dados do usuário.
    """
    payload = request.get_json(force=True, silent=True) or {}
    email = (
        payload.get("email")
        or payload.get("user")
        or payload.get("usuario")
        or payload.get("username")
        or ""
    ).strip().lower()
    senha = (payload.get("senha") or payload.get("password") or "").strip()

    if not email or not senha:
        return jsonify({"ok": False, "error": "Informe email e senha"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            user = _fetch_user_by_email(cur, email)
            if not user or not user["ativo"]:
                return jsonify({"ok": False, "error": "Usuário/senha inválidos"}), 401
            if not user.get("senha_hash") or not verify_password(senha, user["senha_hash"]):
                return jsonify({"ok": False, "error": "Usuário/senha inválidos"}), 401

            token = _issue_token(user)
            return jsonify({
                "ok": True,
                "token": token,
                "user": {
                    "id": user["id"],
                    "nome": user["nome"],
                    "email": user["email"],
                    "setor_id": user["setor_id"],
                    "nivel": user["nivel"],
                    "perfil": ROLE_MAP.get(user["nivel"], str(user["nivel"]))
                }
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/me", methods=["GET"])
@require_level(1)
def api_me():
    user = request.current_user
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            db_user = _fetch_user_by_id(cur, int(user['id']))
            if not db_user or not db_user.get('ativo'):
                return jsonify({"ok": False, "error": "Usuario inativo"}), 401
            return jsonify({
                "ok": True,
                "user": {
                    "id": db_user['id'],
                    "nome": db_user['nome'],
                    "email": db_user['email'],
                    "setor_id": db_user['setor_id'],
                    "nivel": db_user['nivel'],
                    "perfil": ROLE_MAP.get(db_user['nivel'], str(db_user['nivel']))
                }
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# 8) SETORES / INDICADORES (GET)
# =========================
@app.route("/api/setores", methods=["GET"])
def api_setores():
    """
    - Sem token: lista setores ativos (para UI pública, se quiser).
    - Com token nível <4: lista apenas o setor do usuário.
    - Gestão/ADM: lista todos.
    """
    user = get_current_user(optional=True)

    with get_db_connection() as conn:
        cur = conn.cursor()

        if user and not _is_gestao_or_admin(user):
            setor_ids = set()
            if user.get("setor_id") is not None:
                setor_ids.add(int(user["setor_id"]))

            if int(user.get("nivel") or 1) in (2, 3):
                setor_ids.update(_get_assigned_sector_ids(cur, int(user["id"])))

            if not setor_ids:
                return jsonify([])

            placeholders = ",".join(["?"] * len(setor_ids))
            cur.execute(
                f"SELECT ZSE_ID, ZSE_NOME, ZSE_ATIVO FROM ZSE WHERE ZSE_ATIVO = 1 AND ZSE_ID IN ({placeholders}) ORDER BY ZSE_NOME",
                tuple(setor_ids)
            )
        else:
            cur.execute("SELECT ZSE_ID, ZSE_NOME, ZSE_ATIVO FROM ZSE WHERE ZSE_ATIVO = 1 ORDER BY ZSE_NOME")

        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))

@app.route("/api/gestor/funcionarios", methods=["GET"])
@require_level(3)
def api_gestor_funcionarios():
    """Lista funcionarios do setor do lider (nivel 3+)."""
    user = request.current_user
    if not user.get("setor_id"):
        return jsonify([])
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZFU_ID, ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_ATIVO "
                "FROM ZFU WHERE ZFU_SETOR_ID = ? AND ZFU_ATIVO = 1 ORDER BY ZFU_NOME",
                (int(user["setor_id"]),)
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/setores", methods=["POST"])
@require_level(4)
def api_create_setor():
    payload = request.get_json(force=True, silent=True) or {}
    nome = (payload.get("nome") or "").strip()

    if not nome:
        return jsonify({"ok": False, "error": "Informe nome do setor"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM ZSE WHERE LOWER(ZSE_NOME) = LOWER(?)", (nome,))
            if cur.fetchone():
                return jsonify({"ok": False, "error": "Setor ja existe"}), 409

            cur.execute(
                "INSERT INTO ZSE (ZSE_NOME, ZSE_ATIVO) VALUES (?, 1)",
                (nome,)
            )
            conn.commit()
            _log_action(request.current_user, 'setor_criar', f"nome={nome}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/setores/<int:setor_id>", methods=["PUT"])
@require_level(4)
def api_update_setor(setor_id: int):
    payload = request.get_json(force=True, silent=True) or {}
    fields = []
    params = []

    if "nome" in payload:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            return jsonify({"ok": False, "error": "Informe nome do setor"}), 400
        fields.append("ZSE_NOME = ?")
        params.append(nome)

    if "ativo" in payload:
        ativo = 1 if payload.get("ativo") else 0
        fields.append("ZSE_ATIVO = ?")
        params.append(ativo)

    if not fields:
        return jsonify({"ok": False, "error": "Nada para atualizar"}), 400

    params.append(setor_id)

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE ZSE SET {', '.join(fields)} WHERE ZSE_ID = ?",
                params
            )
            conn.commit()
            _log_action(request.current_user, 'setor_atualizar', f"setor_id={setor_id}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/indicadores", methods=["GET"])
def api_indicadores():
    """
    GET /api/indicadores?setorId=1
    - Sem token: permite se quiser (aqui exige setorId)
    - Com token nivel <4: so pode ver do proprio setor ou setores atribuidos
    - Gestao/ADM: pode ver todos
    """
    user = get_current_user(optional=True)
    setor_id = request.args.get("setorId") or request.args.get("setor_id")

    with get_db_connection() as conn:
        cur = conn.cursor()

        if setor_id:
            setor_id_int = int(setor_id)
            filter_mode = "all"

            if user and not _is_gestao_or_admin(user):
                allowed = False
                if user.get("setor_id") is not None and int(user["setor_id"]) == setor_id_int:
                    allowed = True
                    filter_mode = "own"
                elif int(user.get("nivel") or 1) in (2, 3):
                    assigned = _get_assigned_sector_ids(cur, int(user["id"]))
                    if setor_id_int in assigned:
                        allowed = True
                        filter_mode = "assigned"

                if not allowed:
                    return jsonify({"ok": False, "error": "Acesso negado a este setor"}), 403

            if user and not _is_gestao_or_admin(user):
                if filter_mode == "assigned":
                    cur.execute(
                        "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_RESPONSAVEL_ID "
                        "FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_SETOR_ID = ? AND ZIN_RESPONSAVEL_ID = ? ORDER BY ZIN_CODIGO",
                        (setor_id_int, int(user["id"]))
                    )
                else:
                    if int(user.get("nivel") or 1) == 2:
                        cur.execute(
                            "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_RESPONSAVEL_ID "
                            "FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_SETOR_ID = ? AND (ZIN_RESPONSAVEL_ID IS NULL OR ZIN_RESPONSAVEL_ID = ?) ORDER BY ZIN_CODIGO",
                            (setor_id_int, int(user["id"]))
                        )
                    else:
                        cur.execute(
                            "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_RESPONSAVEL_ID "
                            "FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_SETOR_ID = ? ORDER BY ZIN_CODIGO",
                            (setor_id_int,)
                        )
            else:
                cur.execute(
                    "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_RESPONSAVEL_ID "
                    "FROM ZIN WHERE ZIN_ATIVO = 1 AND ZIN_SETOR_ID = ? ORDER BY ZIN_CODIGO",
                    (setor_id_int,)
                )
        else:
            # para nao expor sem setorId
            if user and not _is_gestao_or_admin(user):
                return jsonify({"ok": False, "error": "Informe setorId/setor_id"}), 400

            cur.execute(
                "SELECT ZIN_ID, ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_RESPONSAVEL_ID "
                "FROM ZIN WHERE ZIN_ATIVO = 1 ORDER BY ZIN_SETOR_ID, ZIN_CODIGO"
            )

        rows = cur.fetchall()
        items = _rows_to_dicts(cur, rows)
        if user and int(user.get("nivel") or 1) == 3:
            for item in items:
                resp = item.get("ZIN_RESPONSAVEL_ID")
                if resp is not None and int(resp) != int(user["id"]):
                    item["read_only"] = True
                else:
                    item["read_only"] = False
        if user and int(user.get("nivel") or 1) == 1:
            for item in items:
                item["read_only"] = True

        return jsonify(items)

# =========================
# 9) VALORES (DEFINITIVO) - GET/POST
# =========================
@app.route("/api/valores", methods=["GET"])
@require_level(1)
def api_listar_valores():
    user = request.current_user
    setor_id = request.args.get("setorId") or request.args.get("setor_id")
    periodo = request.args.get("periodo")

    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    setor_id = int(setor_id)
    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError:
        allowed = False
        if int(user.get("nivel") or 1) in (2, 3):
            with get_db_connection() as conn:
                cur = conn.cursor()
                assigned = _get_assigned_sector_ids(cur, int(user["id"]))
                if int(setor_id) in assigned:
                    allowed = True
        if not allowed:
            return jsonify({"ok": False, "error": "Acesso negado a este setor"}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZIV_ID, ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM "
                "FROM ZIV WHERE ZIV_SETOR_ID = ? AND ZIV_PERIODO = ? ORDER BY ZIV_INDICADOR_ID",
                (setor_id, p)
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/valores", methods=["POST"])
@require_level(3)
def api_salvar_valores_definitivos():
    """
    Somente nível 3+ (LIDER) salva definitivo.
    Payload robusto (aceita varios aliases).
    """
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}

    setor_id = _pick(payload, "setorId", "setor_id", "setorID")
    setor_nome = _pick(payload, "setorNome", "setor_nome", "setor", "nomeSetor", "nome_setor")

    funcionario_id = _pick(payload, "funcionarioId", "funcionario_id", "usuarioId", "usuario_id")
    funcionario_email = _pick(payload, "funcionarioEmail", "funcionario_email", "email")
    funcionario_nome = _pick(payload, "funcionarioNome", "funcionario_nome", "nome", "usuarioNome", "usuario_nome")

    periodo = _pick(payload, "periodo", "competencia", "mes", "period")
    valores = _pick(payload, "valores", "itens", "items", default=[]) or []

    if (not setor_id and not setor_nome):
        return jsonify({"ok": False, "error": "Envie setorId/setor_id ou setorNome/setor_nome"}), 400
    if (not funcionario_id and not (funcionario_email or funcionario_nome)):
        return jsonify({"ok": False, "error": "Envie funcionarioId/funcionario_id ou funcionarioEmail/email ou funcionarioNome/nome"}), 400
    if not periodo:
        return jsonify({"ok": False, "error": "Envie periodo (YYYY-MM ou YYYY-MM-01)"}), 400
    if not isinstance(valores, list):
        return jsonify({"ok": False, "error": "valores precisa ser uma lista"}), 400

    # normaliza periodo
    try:
        p = str(periodo)
        if len(p) == 7:
            periodo_date = datetime.strptime(p + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(p, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"ok": False, "error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)

            # RBAC setor (permite setor atribuido para nivel 2/3)
            try:
                _enforce_setor_access(user, int(setor_id_db))
            except PermissionError:
                allowed = False
                if int(user.get("nivel") or 1) in (2, 3):
                    assigned = _get_assigned_sector_ids(cur, int(user["id"]))
                    if int(setor_id_db) in assigned:
                        allowed = True
                if not allowed:
                    return jsonify({'ok': False, 'error': 'Acesso negado a este setor'}), 403

            funcionario_id_db = _get_or_create_funcionario(
                cur, funcionario_id, funcionario_email, funcionario_nome,
                setor_id=setor_id_db
            )

            status = "PENDING" if int(user.get("nivel") or 1) == 2 else "DRAFT"

            for item in valores:
                if not isinstance(item, dict):
                    continue

                ind_id = _pick(item, "indicadorId", "indicador_id", "id")
                ind_codigo = _pick(item, "indicadorCodigo", "indicador_codigo", "codigo", "code")
                ind_nome = _pick(item, "indicadorNome", "indicador_nome", "nome", "name")
                ind_tipo = _pick(item, "tipo", "type")
                ind_unidade = _pick(item, "unidade", "unit")
                ind_meta = _pick(item, "meta", "target")
                valor = _pick(item, "valor", "value")

                if not ind_id and ind_codigo is None:
                    continue

                ind_id_db = _get_or_create_indicador(
                    cur, ind_id, setor_id_db, ind_codigo,
                    ind_nome or f"Indicador {ind_codigo}",
                    tipo=ind_tipo, unidade=ind_unidade, meta=ind_meta
                )

                ind_setor_id, resp_id = _get_indicator_access(cur, ind_id_db)
                if ind_setor_id is None:
                    return jsonify({"ok": False, "error": "Indicador nao encontrado"}), 400
                if int(user.get("nivel") or 1) < 4:
                    if not _can_user_fill_indicator(user, ind_setor_id, resp_id):
                        return jsonify({"ok": False, "error": "Sem permissao para preencher este indicador"}), 403

                cur.execute("""
                    MERGE ZIV AS tgt
                    USING (SELECT ? AS ZIV_INDICADOR_ID, ? AS ZIV_SETOR_ID, ? AS ZIV_PERIODO) AS src
                    ON tgt.ZIV_INDICADOR_ID = src.ZIV_INDICADOR_ID AND tgt.ZIV_SETOR_ID = src.ZIV_SETOR_ID AND tgt.ZIV_PERIODO = src.ZIV_PERIODO
                    WHEN MATCHED THEN
                        UPDATE SET ZIV_VALOR = ?, ZIV_ATUALIZADO_EM = ?, ZIV_FUNCIONARIO_ID = ?
                    WHEN NOT MATCHED THEN
                        INSERT (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                ind_id_db, setor_id_db, periodo_date,
                str(valor) if valor is not None else None, now, funcionario_id_db,
                ind_id_db, setor_id_db, funcionario_id_db, periodo_date,
                str(valor) if valor is not None else None, now, now)

            conn.commit()

        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        print("[ERRO] /api/valores:", str(e))
        print(traceback.format_exc())
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# 10) DRAFTS (rascunhos) - POST/GET/SUBMIT/APPROVE
# =========================
@app.route("/api/drafts", methods=["POST"])
@require_level(2)
def api_salvar_draft():
    """
    Nível 2+: salva rascunhos.
    """
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}

    setor_id = _pick(payload, "setorId", "setor_id", "setorID")
    setor_nome = _pick(payload, "setorNome", "setor_nome", "setor", "nomeSetor", "nome_setor")

    funcionario_id = _pick(payload, "funcionarioId", "funcionario_id", "usuarioId", "usuario_id")
    funcionario_email = _pick(payload, "funcionarioEmail", "funcionario_email", "email")
    funcionario_nome = _pick(payload, "funcionarioNome", "funcionario_nome", "nome", "usuarioNome", "usuario_nome")

    periodo = _pick(payload, "periodo", "competencia", "mes", "period")
    valores = _pick(payload, "valores", "itens", "items", default=[]) or []

    if (not setor_id and not setor_nome):
        return jsonify({"ok": False, "error": "Envie setorId/setor_id ou setorNome/setor_nome"}), 400
    if (not funcionario_id and not (funcionario_email or funcionario_nome)):
        return jsonify({"ok": False, "error": "Envie funcionarioId/funcionario_id ou funcionarioEmail/email ou funcionarioNome/nome"}), 400
    if not periodo:
        return jsonify({"ok": False, "error": "Envie periodo (YYYY-MM ou YYYY-MM-01)"}), 400
    if not isinstance(valores, list):
        return jsonify({"ok": False, "error": "valores precisa ser uma lista"}), 400

    # normaliza periodo
    try:
        p = str(periodo)
        if len(p) == 7:
            periodo_date = datetime.strptime(p + "-01", "%Y-%m-%d").date()
        else:
            periodo_date = datetime.strptime(p, "%Y-%m-%d").date()
        periodo_date = periodo_date.replace(day=1)
    except Exception:
        return jsonify({"ok": False, "error": "periodo inválido. Use YYYY-MM ou YYYY-MM-01"}), 400

    now = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            setor_id_db = _get_or_create_setor(cur, setor_id, setor_nome)

            # RBAC setor
            try:
                _enforce_setor_access(user, int(setor_id_db))
            except PermissionError as e:
                return jsonify({'ok': False, 'error': str(e)}), 403

            funcionario_id_db = _get_or_create_funcionario(
                cur, funcionario_id, funcionario_email, funcionario_nome,
                setor_id=setor_id_db
            )

            for item in valores:
                if not isinstance(item, dict):
                    continue

                ind_id = _pick(item, "indicadorId", "indicador_id", "id")
                ind_codigo = _pick(item, "indicadorCodigo", "indicador_codigo", "codigo", "code")
                ind_nome = _pick(item, "indicadorNome", "indicador_nome", "nome", "name")
                ind_tipo = _pick(item, "tipo", "type")
                ind_unidade = _pick(item, "unidade", "unit")
                ind_meta = _pick(item, "meta", "target")
                valor = _pick(item, "valor", "value")

                if not ind_id and ind_codigo is None:
                    continue

                ind_id_db = _get_or_create_indicador(
                    cur, ind_id, setor_id_db, ind_codigo,
                    ind_nome or f"Indicador {ind_codigo}",
                    tipo=ind_tipo, unidade=ind_unidade, meta=ind_meta
                )

                ind_setor_id, resp_id = _get_indicator_access(cur, ind_id_db)
                if ind_setor_id is None:
                    return jsonify({"ok": False, "error": "Indicador nao encontrado"}), 400
                if int(user.get("nivel") or 1) < 4:
                    if not _can_user_fill_indicator(user, ind_setor_id, resp_id):
                        return jsonify({"ok": False, "error": "Sem permissao para preencher este indicador"}), 403

                cur.execute(
                    """
                    INSERT INTO ZDR (ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_STATUS, ZDR_CRIADO_EM)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ind_id_db, setor_id_db, funcionario_id_db, periodo_date,
                     str(valor) if valor is not None else None, status, now)
                )

            conn.commit()

        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        print("[ERRO] /api/drafts:", str(e))
        print(traceback.format_exc())
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts", methods=["GET"])
@require_level(2)
def api_listar_drafts():
    """
    Lista drafts.
    - Editor (nível 2): vê apenas os próprios drafts
    - Líder (3): vê do seu setor
    - Gestão/ADM: vê tudo (filtrável por setor/período)
    """
    user = request.current_user
    setor_id = request.args.get("setorId") or request.args.get("setor_id")
    periodo = request.args.get("periodo")

    with get_db_connection() as conn:
        cur = conn.cursor()

        where = ["1=1"]
        params = []

        if setor_id:
            where.append("ZDR_SETOR_ID = ?")
            params.append(int(setor_id))

        if periodo:
            p = str(periodo)
            if len(p) == 7:
                p = p + "-01"
            where.append("ZDR_PERIODO = ?")
            params.append(p)

        if not _is_gestao_or_admin(user):
            if int(user["nivel"]) == 2:
                where.append("ZDR_FUNCIONARIO_ID = ?")
                params.append(int(user["id"]))
            else:
                if user.get("setor_id") is not None:
                    where.append("ZDR_SETOR_ID = ?")
                    params.append(int(user["setor_id"]))
                else:
                    where.append("1=0")

        sql = f"""
            SELECT
                ZDR_ID, ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID,
                ZDR_PERIODO, ZDR_VALOR, ZDR_STATUS,
                ZDR_CRIADO_EM, ZDR_ENVIADO_EM, ZDR_APROVADO_EM, ZDR_APROVADO_POR,
                ZDR_REJEITADO_EM, ZDR_REJEITADO_POR, ZDR_REJEITADO_MOTIVO
            FROM ZDR
            WHERE {' AND '.join(where)}
            ORDER BY ZDR_CRIADO_EM DESC
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        return jsonify(_rows_to_dicts(cur, rows))

@app.route("/api/drafts/rejected", methods=["GET"])
@require_level(2)
def api_listar_drafts_rejeitados():
    user = request.current_user
    setor_id = request.args.get("setorId") or request.args.get("setor_id")

    where = ["d.ZDR_STATUS = 'REJECTED'", "d.ZDR_FUNCIONARIO_ID = ?"]
    params = [int(user["id"])]

    if setor_id:
        where.append("d.ZDR_SETOR_ID = ?")
        params.append(int(setor_id))

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT
                    d.ZDR_ID,
                    d.ZDR_INDICADOR_ID,
                    i.ZIN_NOME AS INDICADOR_NOME,
                    d.ZDR_SETOR_ID,
                    d.ZDR_PERIODO,
                    d.ZDR_REJEITADO_MOTIVO,
                    d.ZDR_REJEITADO_EM
                FROM ZDR d
                INNER JOIN ZIN i ON i.ZIN_ID = d.ZDR_INDICADOR_ID
                WHERE {' AND '.join(where)}
                ORDER BY d.ZDR_REJEITADO_EM DESC
                """,
                params
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts/pending", methods=["GET"])
@require_level(3)
def api_listar_drafts_pendentes():
    """Lista drafts pendentes de aprovacao do setor do lider."""
    user = request.current_user
    setor_id = request.args.get("setorId") or request.args.get("setor_id")

    if not _is_gestao_or_admin(user):
        setor_id = user.get("setor_id")

    if not setor_id:
        return jsonify({"ok": False, "error": "Informe setor_id"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    d.ZDR_ID,
                    d.ZDR_INDICADOR_ID,
                    i.ZIN_NOME AS INDICADOR_NOME,
                    d.ZDR_SETOR_ID,
                    s.ZSE_NOME AS SETOR_NOME,
                    d.ZDR_FUNCIONARIO_ID,
                    f.ZFU_NOME AS FUNCIONARIO_NOME,
                    d.ZDR_PERIODO,
                    d.ZDR_VALOR,
                    d.ZDR_STATUS,
                    d.ZDR_CRIADO_EM
                FROM ZDR d
                INNER JOIN ZIN i ON i.ZIN_ID = d.ZDR_INDICADOR_ID
                INNER JOIN ZSE s ON s.ZSE_ID = d.ZDR_SETOR_ID
                LEFT JOIN ZFU f ON f.ZFU_ID = d.ZDR_FUNCIONARIO_ID
                WHERE d.ZDR_STATUS = 'PENDING' AND d.ZDR_SETOR_ID = ?
                ORDER BY d.ZDR_CRIADO_EM DESC
                """,
                (int(setor_id),)
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts/submit", methods=["POST"])
@require_level(2)
def api_submit_drafts():
    """
    Marca drafts como PENDING (para aprovação).
    - Editor: só envia os próprios drafts
    - Líder/Gestão/ADM: envia do setor/período (se quiser)
    """
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = payload.get("setor_id") or payload.get("setorId")
    periodo = payload.get("periodo")

    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    setor_id = int(setor_id)

    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            where = "ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS IN ('DRAFT','REJECTED')"
            params = [setor_id, p]

            if int(user["nivel"]) == 2:
                where += " AND ZDR_FUNCIONARIO_ID = ?"
                params.append(int(user["id"]))

            cur.execute(
                f"UPDATE ZDR SET ZDR_STATUS='PENDING', ZDR_ENVIADO_EM = SYSUTCDATETIME() WHERE {where}",
                params
            )
            conn.commit()
            _log_action(request.current_user, 'user_criar', f"email={email}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts/approve", methods=["POST"])
@require_level(3)
def api_approve_drafts():
    """
    Aprova drafts PENDING e grava em definitivo (ZIV).
    Nível 3+.
    """
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = int(payload.get("setor_id") or payload.get("setorId") or 0)
    periodo = payload.get("periodo")

    if not setor_id or not periodo:
        return jsonify({"ok": False, "error": "Informe setor_id e periodo"}), 400

    try:
        _enforce_setor_access(user, setor_id)
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403

    p = str(periodo)
    if len(p) == 7:
        p = p + "-01"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                "SELECT ZDR_INDICADOR_ID, ZDR_VALOR, ZDR_FUNCIONARIO_ID "
                "FROM ZDR WHERE ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS = 'PENDING'",
                (setor_id, p)
            )
            items = cur.fetchall()

            if not items:
                return jsonify({"ok": False, "error": "Não há rascunhos PENDING para aprovar"}), 400

            for ind_id, valor, func_id in items:
                cur.execute(
                    "SELECT ZIV_ID FROM ZIV WHERE ZIV_INDICADOR_ID = ? AND ZIV_SETOR_ID = ? AND ZIV_PERIODO = ?",
                    (ind_id, setor_id, p)
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE ZIV SET ZIV_VALOR = ?, ZIV_FUNCIONARIO_ID = ?, ZIV_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZIV_ID = ?",
                        (valor, func_id, row[0])
                    )
                else:
                    cur.execute(
                        "INSERT INTO ZIV (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM) "
                        "VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME(), SYSUTCDATETIME())",
                        (ind_id, setor_id, func_id, p, valor)
                    )

            cur.execute(
                "UPDATE ZDR SET ZDR_STATUS='APPROVED', ZDR_APROVADO_EM = SYSUTCDATETIME(), ZDR_APROVADO_POR = ? "
                "WHERE ZDR_SETOR_ID = ? AND ZDR_PERIODO = ? AND ZDR_STATUS = 'PENDING'",
                (int(user["id"]), setor_id, p)
            )

            conn.commit()
            _log_action(request.current_user, 'drafts_aprovar', f"setor_id={setor_id} periodo={p} qtd={len(items)}")
            return jsonify({"ok": True, "aprovados": len(items)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts/<int:draft_id>/approve", methods=["POST"])
@require_level(3)
def api_approve_draft_item(draft_id: int):
    user = request.current_user
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZDR_INDICADOR_ID, ZDR_SETOR_ID, ZDR_FUNCIONARIO_ID, ZDR_PERIODO, ZDR_VALOR, ZDR_STATUS "
                "FROM ZDR WHERE ZDR_ID = ?",
                (int(draft_id),)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "error": "Draft nao encontrado"}), 404

            ind_id, setor_id, func_id, periodo, valor, status = row
            if status != "PENDING":
                return jsonify({"ok": False, "error": "Draft nao esta pendente"}), 400

            _enforce_setor_access(user, int(setor_id))

            now = datetime.utcnow()
            cur.execute("""
                MERGE ZIV AS tgt
                USING (SELECT ? AS ZIV_INDICADOR_ID, ? AS ZIV_SETOR_ID, ? AS ZIV_PERIODO) AS src
                ON tgt.ZIV_INDICADOR_ID = src.ZIV_INDICADOR_ID AND tgt.ZIV_SETOR_ID = src.ZIV_SETOR_ID AND tgt.ZIV_PERIODO = src.ZIV_PERIODO
                WHEN MATCHED THEN
                    UPDATE SET ZIV_VALOR = ?, ZIV_ATUALIZADO_EM = ?, ZIV_FUNCIONARIO_ID = ?
                WHEN NOT MATCHED THEN
                    INSERT (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_FUNCIONARIO_ID, ZIV_PERIODO, ZIV_VALOR, ZIV_CRIADO_EM, ZIV_ATUALIZADO_EM)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            ind_id, setor_id, periodo,
            valor, now, func_id,
            ind_id, setor_id, func_id, periodo, valor, now, now)

            cur.execute(
                "UPDATE ZDR SET ZDR_STATUS='APPROVED', ZDR_APROVADO_EM = SYSUTCDATETIME(), ZDR_APROVADO_POR = ? "
                "WHERE ZDR_ID = ?",
                (int(user["id"]), int(draft_id))
            )

            conn.commit()
            _log_action(request.current_user, 'draft_aprovar', f"draft_id={draft_id}")
            return jsonify({"ok": True})
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/drafts/<int:draft_id>/reject", methods=["POST"])
@require_level(3)
def api_reject_draft_item(draft_id: int):
    user = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    motivo = (payload.get("motivo") or "").strip()

    if not motivo:
        return jsonify({"ok": False, "error": "Informe o motivo"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZDR_SETOR_ID, ZDR_STATUS FROM ZDR WHERE ZDR_ID = ?",
                (int(draft_id),)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "error": "Draft nao encontrado"}), 404

            setor_id, status = row
            if status != "PENDING":
                return jsonify({"ok": False, "error": "Draft nao esta pendente"}), 400

            _enforce_setor_access(user, int(setor_id))

            cur.execute(
                "UPDATE ZDR SET ZDR_STATUS='REJECTED', ZDR_REJEITADO_EM = SYSUTCDATETIME(), "
                "ZDR_REJEITADO_POR = ?, ZDR_REJEITADO_MOTIVO = ? WHERE ZDR_ID = ?",
                (int(user["id"]), motivo, int(draft_id))
            )
            conn.commit()
            _log_action(request.current_user, 'draft_rejeitar', f"draft_id={draft_id}")
            return jsonify({"ok": True})
    except PermissionError as e:
        return jsonify({"ok": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# 11) GESTÃO/ADM - USERS CRUD
# =========================
@app.route("/api/users", methods=["GET"])
@require_level(4)
def api_list_users():
    """Lista usuários (somente Gestão/ADM)."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ZFU_ID, ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_ATIVO, ZFU_CRIADO_EM, ZFU_ATUALIZADO_EM "
                "FROM ZFU ORDER BY ZFU_NIVEL DESC, ZFU_NOME"
            )
            rows = cur.fetchall()
            return jsonify(_rows_to_dicts(cur, rows))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/users", methods=["POST"])
@require_level(4)
def api_create_user():
    """Cria usuário. Gestão não pode criar níveis >= ao próprio."""
    admin = request.current_user
    payload = request.get_json(force=True, silent=True) or {}

    nome = (payload.get("nome") or "").strip()
    email = (payload.get("email") or "").strip()
    senha = payload.get("senha") or payload.get("password") or "1234"
    setor_id = payload.get("setor_id") or payload.get("setorId")
    nivel = int(payload.get("nivel") or 1)

    if not nome or not email:
        return jsonify({"ok": False, "error": "Informe nome e email"}), 400

    if int(admin["nivel"]) < 5 and nivel >= int(admin["nivel"]):
        return jsonify({"ok": False, "error": "Você só pode criar usuários abaixo do seu nível"}), 403

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM ZFU WHERE LOWER(ZFU_EMAIL)=LOWER(?)", (email,))
            if cur.fetchone():
                return jsonify({"ok": False, "error": "Email já cadastrado"}), 409

            cur.execute(
                "INSERT INTO ZFU (ZFU_NOME, ZFU_EMAIL, ZFU_SETOR_ID, ZFU_NIVEL, ZFU_SENHA_HASH, ZFU_ATIVO, ZFU_CRIADO_EM) "
                "VALUES (?, ?, ?, ?, ?, 1, SYSUTCDATETIME())",
                (nome, email, setor_id, nivel, hash_password(senha))
            )
            conn.commit()
            _log_action(request.current_user, 'user_atualizar', f"user_id={user_id}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/users/<int:user_id>", methods=["PUT"])
@require_level(4)
def api_update_user(user_id: int):
    """Atualiza usuário. Gestão não pode mexer em usuário do mesmo nível ou acima."""
    admin = request.current_user
    payload = request.get_json(force=True, silent=True) or {}

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute("SELECT ZFU_NIVEL FROM ZFU WHERE ZFU_ID = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "error": "Usuário não encontrado"}), 404
            target_level = int(row[0] or 1)

            if int(admin["nivel"]) < 5 and target_level >= int(admin["nivel"]):
                return jsonify({"ok": False, "error": "Você não pode editar usuário do mesmo nível ou acima"}), 403

            fields = []
            params = []

            if "nivel" in payload:
                new_level = int(payload.get("nivel") or 1)
                if int(admin["nivel"]) < 5 and new_level >= int(admin["nivel"]):
                    return jsonify({"ok": False, "error": "Você só pode atribuir níveis abaixo do seu"}), 403
                fields.append("ZFU_NIVEL = ?")
                params.append(new_level)

            for k, col in [("nome", "ZFU_NOME"), ("email", "ZFU_EMAIL"), ("setor_id", "ZFU_SETOR_ID"), ("ativo", "ZFU_ATIVO")]:
                if k in payload:
                    fields.append(f"{col} = ?")
                    params.append(payload[k])

            if not fields:
                return jsonify({"ok": False, "error": "Nada para atualizar"}), 400

            params.append(user_id)
            cur.execute(
                f"UPDATE ZFU SET {', '.join(fields)}, ZFU_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZFU_ID = ?",
                params
            )
            conn.commit()
            _log_action(request.current_user, 'user_reset_senha', f"user_id={user_id}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/users/<int:user_id>/reset-password", methods=["POST"])
@require_level(4)
def api_reset_password(user_id: int):
    """Redefine senha. Gestão não pode resetar senha de nível igual/acima."""
    admin = request.current_user
    payload = request.get_json(force=True, silent=True) or {}
    new_pass = payload.get("senha") or payload.get("password") or "1234"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute("SELECT ZFU_NIVEL FROM ZFU WHERE ZFU_ID = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "error": "Usuário não encontrado"}), 404
            target_level = int(row[0] or 1)

            if int(admin["nivel"]) < 5 and target_level >= int(admin["nivel"]):
                return jsonify({"ok": False, "error": "Você não pode redefinir senha de usuário do mesmo nível ou acima"}), 403

            cur.execute(
                "UPDATE ZFU SET ZFU_SENHA_HASH = ?, ZFU_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZFU_ID = ?",
                (hash_password(new_pass), user_id)
            )
            conn.commit()
            _log_action(request.current_user, 'indicador_criar', f"setor_id={setor_id} codigo={codigo}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# 12) GESTÃO/ADM - INDICADORES CRUD
# =========================
@app.route("/api/indicadores", methods=["POST"])
@require_level(4)
def api_create_indicador():
    payload = request.get_json(force=True, silent=True) or {}
    setor_id = int(payload.get("setor_id") or payload.get("setorId") or 0)
    codigo = (payload.get("codigo") or "").strip()
    nome = (payload.get("nome") or "").strip()
    tipo = payload.get("tipo")
    unidade = payload.get("unidade")
    meta = payload.get("meta")
    responsavel_id = payload.get("responsavel_id") or payload.get("responsavelId")
    if responsavel_id in ("", None):
        responsavel_id = None
    else:
        responsavel_id = int(responsavel_id)

    if not setor_id or not codigo or not nome:
        return jsonify({"ok": False, "error": "Informe setor_id, codigo e nome"}), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO ZIN (ZIN_SETOR_ID, ZIN_CODIGO, ZIN_NOME, ZIN_TIPO, ZIN_UNIDADE, ZIN_META, ZIN_ATIVO, ZIN_CRIADO_EM, ZIN_RESPONSAVEL_ID) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, SYSUTCDATETIME(), ?)",
                (setor_id, codigo, nome, tipo, unidade, meta, responsavel_id)
            )
            conn.commit()
            _log_action(request.current_user, 'indicador_atualizar', f"indicador_id={indicador_id}")
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/indicadores/<int:indicador_id>", methods=["PUT"])
@require_level(4)
def api_update_indicador(indicador_id: int):
    payload = request.get_json(force=True, silent=True) or {}
    fields = []
    params = []

    for col, key in [
        ("ZIN_NOME", "nome"),
        ("ZIN_TIPO", "tipo"),
        ("ZIN_UNIDADE", "unidade"),
        ("ZIN_META", "meta"),
        ("ZIN_ATIVO", "ativo"),
    ]:
        if key in payload:
            fields.append(f"{col} = ?")
            params.append(payload[key])

    if "responsavel_id" in payload or "responsavelId" in payload:
        resp_id = payload.get("responsavel_id") if "responsavel_id" in payload else payload.get("responsavelId")
        if resp_id in ("", None):
            resp_id = None
        else:
            resp_id = int(resp_id)
        fields.append("ZIN_RESPONSAVEL_ID = ?")
        params.append(resp_id)

    if not fields:
        return jsonify({"ok": False, "error": "Nada para atualizar"}), 400

    params.append(indicador_id)

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE ZIN SET {', '.join(fields)}, ZIN_ATUALIZADO_EM = SYSUTCDATETIME() WHERE ZIN_ID = ?",
                params
            )
            conn.commit()
            return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# 14) MAIN
# =========================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 SERVIDOR FLASK INICIADO")
    print("=" * 70)
    print("📍 Acesse: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(debug=True, port=5000, host="0.0.0.0", use_reloader=False)
