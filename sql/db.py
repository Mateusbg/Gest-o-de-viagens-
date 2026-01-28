import os

driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
server = os.getenv("SQL_SERVER", "")
database = os.getenv("SQL_DATABASE", "")
user = os.getenv("SQL_USER", "")
password = os.getenv("SQL_PASSWORD", "")
encrypt = os.getenv("SQL_ENCRYPT", "yes")
trust_cert = os.getenv("SQL_TRUST_CERT", "no")

conn_str = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    f"Encrypt={encrypt};"
    f"TrustServerCertificate={trust_cert};"
    "Connection Timeout=10;"
)
