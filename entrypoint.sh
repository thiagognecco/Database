#!/bin/bash
exec gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} -k uvicorn.workers.UvicornWorker app.main:app
