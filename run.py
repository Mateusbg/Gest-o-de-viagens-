import os

from src.app import app

if __name__ == '__main__':
    debug = (os.getenv("FLASK_DEBUG") or os.getenv("DEBUG") or "0").lower() in ("1", "true", "yes", "y")
    host = os.getenv("APP_HOST") or "127.0.0.1"
    port = int(os.getenv("APP_PORT") or "5000")
    app.run(debug=debug, port=port, host=host, use_reloader=False)
