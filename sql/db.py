import os


def build_conn_str() -> str:
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER", "")
    database = os.getenv("SQL_DATABASE", "")
    user = os.getenv("SQL_USER", "")
    password = os.getenv("SQL_PASSWORD", "")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "false").lower() in ("1", "true", "yes", "y")
    encrypt = os.getenv("SQL_ENCRYPT", "yes").lower() in ("1", "true", "yes", "y")
    trust_cert = os.getenv("SQL_TRUST_CERT", "no").lower() in ("1", "true", "yes", "y")
    conn_timeout = int(os.getenv("SQL_CONN_TIMEOUT", "10"))
    app_name = (os.getenv("SQL_APP_NAME") or "").strip()

    enc_part = "Encrypt=yes;" if encrypt else "Encrypt=no;"
    trust_part = "TrustServerCertificate=yes;" if trust_cert else "TrustServerCertificate=no;"

    conn_parts = [
        f"DRIVER={{{driver}}};",
        f"SERVER={server};",
        f"DATABASE={database};",
        enc_part,
        trust_part,
        f"Connection Timeout={conn_timeout};",
    ]
    if trusted:
        conn_parts.append("Trusted_Connection=yes;")
    else:
        conn_parts.append(f"UID={user};PWD={password};")
    if app_name:
        conn_parts.append(f"APP={app_name};")
    return "".join(conn_parts)


conn_str = build_conn_str()
