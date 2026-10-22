FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install --no-cache-dir 'pypdf>=6,<7' 'python-docx>=1.2,<2'
COPY parser.py /app/parser.py
USER 65534:65534
