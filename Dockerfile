# ──────────────────────────────────────────────────────────────
# Stage 1: builder — instala dependências em ambiente isolado
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependências do sistema necessárias para compilar pacotes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas requirements para aproveitar cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ──────────────────────────────────────────────────────────────
# Stage 2: runtime — imagem final reduzida
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Dependências de runtime do PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar pacotes instalados do builder
COPY --from=builder /install /usr/local

# Copiar código da aplicação
COPY app/ ./app/

# Usuário não-root por segurança
RUN useradd -m -u 1000 appuser
USER appuser

# Porta exposta pela API
EXPOSE 8000

# Comando de inicialização da API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
