# Usa uma imagem oficial e leve do Python 3.12 como base
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contentor
WORKDIR /app

# Copia o ficheiro de dependências para dentro do contentor
COPY requirements.txt .

# Instala todas as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código do seu projeto para dentro do contentor
COPY . .

# Expõe a porta 8000 para que possamos aceder à aplicação
EXPOSE 8000

# Define o comando que será executado quando o contentor arrancar
# Isto inicia o servidor Uvicorn de forma que ele seja acessível de fora
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
