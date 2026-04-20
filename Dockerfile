FROM python:3-slim
ADD . /app
WORKDIR /app

RUN pip install --no-cache-dir pygithub

CMD ["python", "/app/main.py"]
