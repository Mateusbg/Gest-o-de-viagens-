from app import app

# Vercel precisa de uma função handler
def handler(request):
    return app(request.environ, request.start_response)
application = app  # Exporte a aplicação Flask como 'application' para Vercel