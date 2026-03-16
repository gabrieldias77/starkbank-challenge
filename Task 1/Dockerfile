FROM public.ecr.aws/lambda/python:3.12

# Copia dependências
COPY requirements.txt .

# Instala dependências no ambiente correto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY app.py .

# Define o handler
CMD ["app.lambda_handler"]