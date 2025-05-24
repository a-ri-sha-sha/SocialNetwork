FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p proto

COPY proto/ ./proto/

COPY *.py .

RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/post_service.proto

CMD ["python", "post_service.py"]
