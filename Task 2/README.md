# Stark Bank Webhook Challenge - Part 2

## Arquitetura: AWS Lambda + API Gateway (Container Image)

Este projeto implementa um webhook para receber notificações de pagamento de invoices do Stark Bank e realizar transferências automáticas.

A implantação é feita via **Container Image** no AWS Lambda.

### Estrutura
- `lambda_function.py`: Código Python da função Lambda.
- `Dockerfile`: Definição da imagem Docker para o Lambda.
- `requirements.txt`: Dependências Python.

### Como Fazer o Deploy (Container)

1.  **Pré-requisitos:**
    - Docker instalado.
    - AWS CLI configurado (`aws configure`).

2.  **Criar Repositório no ECR (Elastic Container Registry):**
    ```bash
    aws ecr create-repository --repository-name starkbank-webhook --image-scanning-configuration scanOnPush=true
    ```

3.  **Build e Push da Imagem:**
    Substitua `123456789012` pelo seu AWS Account ID e `us-east-1` pela sua região.

    ```bash
    # Login no ECR
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

    # Build da imagem
    docker build -t starkbank-webhook .

    # Tag da imagem
    docker tag starkbank-webhook:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/starkbank-webhook:latest

    # Push para o ECR
    docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/starkbank-webhook:latest
    ```

4.  **Criar Função Lambda:**
    - Vá no console AWS Lambda -> Create function.
    - Selecione **Container image**.
    - Dê um nome (ex: `starkbank-webhook`).
    - Em **Container image URI**, clique em *Browse images* e selecione a imagem que você acabou de subir no ECR.
    - Crie a função.

5.  **Configuração:**
    - Vá na aba **Configuration** -> **Environment variables**.
    - Adicione:
        - `PROJECT_ID`: Seu ID do projeto Stark Bank.
        - `ENVIRONMENT`: `sandbox`.
        - `SECRET_NAME`: Nome do segredo no Secrets Manager (default: `starkbank_private_key`).
        - `DYNAMODB_TABLE`: Nome da tabela DynamoDB (default: `StarkBankProcessedInvoices`).

6.  **Configurar Secrets Manager:**
    - Crie um segredo no AWS Secrets Manager chamado `starkbank_private_key`.
    - Cole o conteúdo da sua chave privada (PEM).
    - Dê permissão ao Lambda para ler este segredo (`secretsmanager:GetSecretValue`).

7.  **Configurar DynamoDB (Idempotência):**
    - Crie uma tabela no DynamoDB chamada `StarkBankProcessedInvoices`.
    - Chave de Partição (Partition Key): `invoiceId` (String).
    - (Opcional) Configure TTL no atributo `expireAt` para limpeza automática.
    - Dê permissão ao Lambda para escrever nesta tabela (`dynamodb:PutItem`).

8.  **API Gateway:**
    - Crie uma nova API (HTTP API).
    - Crie uma rota `POST /webhook`.
    - Integre com sua função Lambda.
    - Pegue a URL e configure no dashboard do Stark Bank.
