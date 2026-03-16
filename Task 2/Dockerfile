FROM public.ecr.aws/lambda/python:3.11

# Copia o arquivo de requisitos
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Instala as dependências
RUN pip install -r requirements.txt

# Copia o código da função
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Define o comando para o handler (nome_arquivo.nome_funcao)
CMD [ "lambda_function.lambda_handler" ]
