import os

files = [
    "src/app/__init__.py",
    "src/app/config.py",
    "src/app/logging_config.py",
    "src/app/exceptions.py",
    "src/app/models/__init__.py",
    "src/app/models/domain.py",
    "src/app/repositories/__init__.py",
    "src/app/repositories/base.py",
    "src/app/repositories/s3_repository.py",
    "src/app/repositories/redshift_repository.py",
    "src/app/repositories/metadata_repository.py",
    "src/app/services/__init__.py",
    "src/app/services/validation_service.py",
    "src/app/services/transformation_service.py",
    "src/app/services/dq_service.py",
    "src/app/services/migration_coordinator.py",
    "src/app/validators/__init__.py",
    "src/app/validators/schema_validator.py",
    "src/app/validators/business_validator.py",
    "src/app/utils/__init__.py",
    "src/app/utils/json_utils.py",
    "src/app/utils/s3_path_utils.py",
    "src/app/utils/time_utils.py",
    "src/app/utils/idempotency.py",
    "src/lambdas/ingestion_lambda.py",
    "src/lambdas/validation_lambda.py",
    "src/lambdas/transform_lambda.py",
    "src/lambdas/orchestration_lambda.py",
    "tests/unit/__init__.py",
    "tests/integration/__init__.py",
    "infra/README.md",
    "requirements.txt",
    "README.md",
    ".gitignore"
]

for path in files:
    # Get the directory name
    folder = os.path.dirname(path)
    
    # Only try to create a folder if there IS a folder name
    if folder:
        os.makedirs(folder, exist_ok=True)
        
    # Create the file
    with open(path, 'w') as f:
        pass

print("Folders and files created successfully!")