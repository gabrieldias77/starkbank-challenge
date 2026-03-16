import os
import json
import random
import boto3
import starkbank
from botocore.exceptions import ClientError
from faker import Faker

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

def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    """
    print("Lambda started")
    
    # 1. Retrieve configuration
    project_id = os.environ.get("STARKBANK_PROJECT_ID")
    environment = os.environ.get("STARKBANK_ENV")
    
    # 2. Retrieve private key from Secrets Manager
    try:
        private_key_content = get_secret()
        # Tenta parsear como JSON caso a chave esteja dentro de um objeto JSON no Secrets Manager
        try:
            secret_json = json.loads(private_key_content)
            if 'private_key' in secret_json:
                private_key_content = secret_json['private_key']
        except json.JSONDecodeError:
            pass # Assume que é a string PEM pura
            
    except Exception as e:
        print(f"Failed to setup credentials: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error: Could not retrieve credentials"})
        }

    # 3. Configure StarkBank user
    try:
        user = starkbank.Project(
            environment=environment,
            id=project_id,
            private_key=private_key_content
        )
        starkbank.user = user
    except Exception as e:
        print(f"Error configuring StarkBank user: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error: Configuration failed"})
        }

    # 4. Generate 8 to 12 invoices
    num_invoices = random.randint(8, 12)
    print(f"Generating {num_invoices} invoices")
    
    # Initialize Faker for Brazilian locale to generate valid CPFs and names
    fake = Faker('pt_BR')
    
    invoices_to_create = []
    
    for _ in range(num_invoices):
        # Generate random customer data
        name = fake.name()
        cpf = fake.cpf()
        
        # Random amount between 100.00 and 5000.00 (amount is in cents)
        amount = random.randint(10000, 500000) 
        
        invoices_to_create.append(
            starkbank.Invoice(
                amount=amount,
                name=name,
                tax_id=cpf
            )
        )

    # 5. Send to StarkBank
    try:
        created_invoices = starkbank.invoice.create(invoices_to_create)
        
        invoice_ids = [inv.id for inv in created_invoices]
        print(f"Successfully created {len(created_invoices)} invoices: {invoice_ids}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Created {len(created_invoices)} invoices",
                "invoice_ids": invoice_ids
            })
        }
    except Exception as e:
        print(f"Error creating invoices: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
