import socket
import requests
import os

services = {
    'backend_http': ('127.0.0.1', 8000),
    'frontend_http': ('127.0.0.1', 3000),
    'redis': ('127.0.0.1', 6379),
    'postgres': ('127.0.0.1', 5432),
    'mongo': ('127.0.0.1', 27017),
}

for name, (host, port) in services.items():
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect((host, port))
        print(f"{name}: open ({host}:{port})")
    except Exception as e:
        print(f"{name}: closed ({host}:{port}) -> {e}")
    finally:
        s.close()

# probe backend /live if reachable
try:
    r = requests.get('http://127.0.0.1:8000/live', timeout=2)
    print('backend:/live ->', r.status_code, r.text)
except Exception as e:
    print('backend:/live -> error', e)

# Attempt Redis PING if redis lib available
try:
    import redis
    r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_connect_timeout=1)
    try:
        print('redis ping ->', r.ping())
    except Exception as e:
        print('redis ping -> error', e)
except Exception as e:
    print('redis client not available ->', e)

# Show some env vars relevant to Celery/Redis
print('CELERY_BROKER_URL=', os.environ.get('CELERY_BROKER_URL'))
print('CELERY_RESULT_BACKEND=', os.environ.get('CELERY_RESULT_BACKEND'))
print('GOOGLE_API_KEY=', bool(os.environ.get('GOOGLE_API_KEY')))
print('ALLOWED_HOSTS=', os.environ.get('ALLOWED_HOSTS'))
print('ALLOWED_EXTENSIONS=', os.environ.get('ALLOWED_EXTENSIONS'))
