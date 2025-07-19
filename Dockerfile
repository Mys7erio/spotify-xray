FROM python:3.13-alpine3.22

WORKDIR /src

COPY ./src/requirements.txt .

# Use a cache mount to persist the pip cache directory
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY ./src /src

EXPOSE 80
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]