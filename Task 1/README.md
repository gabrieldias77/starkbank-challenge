# Stark Bank Challenge - Part 1: Invoice Generator

## Arquitetura: AWS Lambda + EventBridge Scheduler (Container Image)

Este projeto implementa um gerador automático de invoices (cobranças) utilizando a SDK do Stark Bank. Ele é executado como uma função AWS Lambda, acionada periodicamente por um Scheduler do EventBridge.

A cada execução, o Lambda gera de **8 a 12 invoices** com valores e dados de clientes aleatórios (utilizando a biblioteca `Faker` para dados brasileiros válidos).

### Estrutura
- `app.py`: Código Python da função Lambda com a lógica de geração de invoices.
- `Dockerfile`: Definição da imagem Docker otimizada para AWS Lambda.
- `requirements.txt`: Dependências do projeto (`starkbank`, `boto3`, `Faker`).

### Fluxo de Execução
1.  **EventBridge Scheduler**: Aciona a função Lambda a cada 3 horas.
2.  **AWS Lambda**:
    - Recupera a chave privada segura do **AWS Secrets Manager**.
    - Gera dados fictícios de clientes (CPF, Nome) e valores aleatórios.
    - Envia as invoices para a API do Stark Bank (ambiente Sandbox).
3.  **Stark Bank**: Processa e cria as invoices.

### Como Fazer o Deploy (Container)

1.  **Pré-requisitos:**
    - Docker instalado e rodando.
    - AWS CLI configurado (`aws configure`).

2.  **Criar Repositório no ECR (Elastic Container Registry):**
    ```bash
    aws ecr create-repository --repository-name starkbank-invoice-generator --region us-east-1
    ```

3.  **Build e Push da Imagem:**
    Substitua `<ACCOUNT_ID>` pelo seu ID da conta AWS e `<REGION>` pela sua região (ex: `us-east-1`).

    ```bash
    # Login no ECR
    aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

    # Build da imagem (Multi-plataforma para compatibilidade com Lambda x86_64)
    docker build --platform linux/amd64 --provenance=false -t starkbank-invoice-generator .

    # Tag da imagem
    docker tag starkbank-invoice-generator:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/starkbank-invoice-generator:latest

    # Push para o ECR
    docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/starkbank-invoice-generator:latest
    ```

4.  **Criar Função Lambda:**
    - Vá no console AWS Lambda -> **Create function**.
    - Selecione **Container image**.
    - Dê um nome (ex: `StarkBankInvoiceGenerator`).
    - Em **Container image URI**, clique em *Browse images* e selecione a imagem que você acabou de subir.
    - Em **Architecture**, certifique-se de selecionar **x86_64**.
    - Crie a função.

5.  **Configuração de Variáveis de Ambiente:**
    - Vá na aba **Configuration** -> **Environment variables**.
    - Adicione as seguintes variáveis:
        - `STARKBANK_PROJECT_ID`: Seu ID do projeto Stark Bank.
        - `STARKBANK_ENV`: `sandbox`.
        - `SECRET_NAME`: Nome do segredo no Secrets Manager (ex: `starkbank_private_key`).
    - **Nota:** Não adicione `AWS_REGION`, ela é configurada automaticamente pela AWS.

6.  **Configurar Secrets Manager:**
    - Vá no console **AWS Secrets Manager** -> **Store a new secret**.
    - Tipo: **Other type of secret**.
    - Em **Plaintext**, cole o conteúdo da sua chave privada (PEM) inteira.
    - Nomeie o segredo como `starkbank_private_key` (ou o nome que definiu na variável `SECRET_NAME`).

7.  **Permissões (IAM Role):**
    - Vá na aba **Configuration** -> **Permissions** da sua Lambda.
    - Clique no nome da Role de execução.
    - Adicione a permissão para ler o segredo:
        ```json
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:starkbank_private_key-*"
        }
        ```

8.  **Configurar EventBridge Scheduler (Cron):**
    - Vá no console **Amazon EventBridge** -> **Schedules**.
    - Clique em **Create schedule**.
    - **Schedule pattern**: Rate-based schedule -> **3 hours**.
    - **Target**: AWS Lambda -> Selecione sua função `StarkBankInvoiceGenerator`.
    - **Timeframe**: Defina uma data de início e fim (para rodar apenas por 24 horas).
    - Crie o agendamento.
