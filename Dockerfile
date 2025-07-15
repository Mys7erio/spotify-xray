FROM python:3.13-alpine3.22

WORKDIR /src

COPY ./src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /src
COPY .env /src/.env

EXPOSE 80
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]