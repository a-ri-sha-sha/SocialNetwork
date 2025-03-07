FROM python:3.12

WORKDIR /app

COPY requirements.txt .
COPY auth-service.py .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "auth-service.py"]
