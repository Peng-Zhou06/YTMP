"""Gunicorn configuration for production"""

bind = '0.0.0.0:5000'

workers = 4

threads = 2

worker_class = 'gevent'

max_requests = 1000
max_requests_jitter = 100

timeout = 120
graceful_timeout = 30

pidfile = '/var/run/ytmp.pid'

accesslog = '/var/log/ytmp/access.log'
errorlog = '/var/log/ytmp/error.log'
loglevel = 'info'

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

preload_app = True

daemon = True