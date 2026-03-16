import json
import os
import time
import boto3
from botocore.exceptions import ClientError
import starkbank
from starkbank import Transfer

def get_secret():
    """
    Retrieves the private key from AWS Secrets Manager.
    """
    secret_name = os.environ.get("SECRET_NAME")
    region_name = os.environ.get("AWS_REGION", "us-east-1")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # Log the error and re-raise or handle appropriately
        print(f"Error retrieving secret {secret_name}: {e}")
        raise e

    # Decrypts secret using the associated KMS key.
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        secret = get_secret_value_response['SecretBinary']
        
    return secret

def acquire_lock(invoice_id):
    """
    Tenta adquirir um 'lock' para esta invoice no DynamoDB.
    Retorna True se conseguiu o lock (primeira vez processando).
    Retorna False se já existe (duplicado).
    """
    table_name = os.environ.get('DYNAMODB_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    try:
        # Tenta inserir o registro apenas se o invoiceId não existir
        table.put_item(
            Item={
                'invoiceId': str(invoice_id),
                'processedAt': str(time.time()),
                # TTL de 30 dias para limpeza automática (opcional, requer config no DynamoDB)
                'expireAt': int(time.time() + (30 * 24 * 60 * 60)) 
            },
            ConditionExpression='attribute_not_exists(invoiceId)'
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Já existe, então é duplicado
            return False
        else:
            # Outro erro (permissão, conexão, etc)
            print(f"Erro ao acessar DynamoDB: {e}")
            raise e

# Configuração do Projeto via Variáveis de Ambiente (Best Practice para AWS Lambda)
def setup_starkbank():
    # Tenta pegar a chave privada do Secrets Manager
    private_key_content = get_secret()
    
    project_id = os.environ.get('PROJECT_ID')
    environment = os.environ.get('ENVIRONMENT', 'sandbox')

    if not private_key_content or not project_id:
        raise Exception("Chave privada (Secrets Manager) e PROJECT_ID são obrigatórios.")

    user = starkbank.Project(
        environment=environment,
        id=project_id,
        private_key=private_key_content
    )
    starkbank.user = user

def lambda_handler(event, context):
    try:
        # Inicializa a autenticação
        setup_starkbank()

        # 1. Obter a assinatura do header e o corpo da requisição
        signature = event['headers'].get('Digital-Signature')
        body = event['body']

        # 2. Verificar e parsear o evento usando a SDK do Stark Bank
        # Isso garante que o evento veio realmente do Stark Bank
        event_obj = starkbank.event.parse(content=body, signature=signature)
        
        # 3. Processar o evento
        # O evento que queremos é 'invoice.credited' (fatura paga)
        if event_obj.subscription == 'invoice' and event_obj.log.type == 'credited':
            invoice = event_obj.log.invoice
            
            # IDEMPOTÊNCIA: Verifica se já processamos esta invoice
            if not acquire_lock(invoice.id):
                print(f"Invoice {invoice.id} já processada anteriormente. Ignorando duplicidade.")
                return {
                    'statusCode': 200,
                    'body': json.dumps('Evento duplicado ignorado.')
                }

            # Calcular o valor a ser transferido (valor recebido - taxas eventuais)
            # O invoice.amount é o valor nominal pago. O invoice.fee é a taxa cobrada pelo Stark Bank.
            fee = invoice.fee if invoice.fee else 0
            amount_to_transfer = invoice.amount - fee
            
            print(f"Invoice {invoice.id} paga. Valor: {invoice.amount}, Taxa: {fee}. Transferindo {amount_to_transfer}...")

            # 4. Criar a transferência
            transfer = Transfer(
                amount=amount_to_transfer,
                bank_code='20018183',
                branch_code='0001',
                account_number='6341320293482496',
                name='Stark Bank S.A.',
                tax_id='20.018.183/0001-80',
                account_type='payment',
                tags=['webhook-transfer', f'invoice-{invoice.id}'] # Tags ajudam a rastrear
            )

            # 5. Enviar a transferência
            transfers = starkbank.transfer.create([transfer])
            
            print(f"Transferência criada: {transfers[0].id}")

        return {
            'statusCode': 200,
            'body': json.dumps('Webhook recebido com sucesso!')
        }

    except Exception as e:
        print(f"Erro no processamento do webhook: {str(e)}")
        # Retornar 200 mesmo em caso de erro interno para evitar retentativas infinitas do webhook
        # se o erro for de lógica nossa (mas 500 se for erro transiente).
        # Para o desafio, 200 é seguro.
        return {
            'statusCode': 200, # Ou 500 se quiser que o Stark Bank tente de novo
            'body': json.dumps(f'Erro: {str(e)}')
        }
