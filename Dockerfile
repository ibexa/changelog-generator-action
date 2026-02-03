FROM python:3.12-slim-bullseye AS builder
ADD . /app
WORKDIR /app

# We are installing dependencies directly into our app source dir
RUN pip install --target=/app pygithub==2.6.1 jira==3.0.1 actions-toolkit==0.1.15

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM python:3.12-slim-bullseye
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
CMD ["python", "/app/main.py"]
