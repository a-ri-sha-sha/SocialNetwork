FROM python:3.12

WORKDIR /app

COPY requirements.txt .
COPY proxy-service.py .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "proxy-service.py"]
