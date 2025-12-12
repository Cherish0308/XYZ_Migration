# Build & Deployment Guide

## Overview

This document describes the build, packaging, and deployment process for the XYZ Migration project. The project uses modern Python packaging standards (PEP 517/518) and provides automated scripts for Lambda deployment.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Building Lambda Packages](#building-lambda-packages)
- [Artifactory Upload](#artifactory-upload)
- [AWS Lambda Deployment](#aws-lambda-deployment)
- [CI/CD Integration](#cicd-integration)
- [Makefile Commands](#makefile-commands)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Python 3.10+**: Project targets Python 3.10-3.12
- **pip**: Latest version recommended
- **AWS CLI**: For Lambda deployments
- **curl**: For Artifactory uploads
- **git**: Version control

### Environment Setup

```bash
# Install development dependencies
make install-dev

# Or manually
pip install -e ".[dev]"
```

### AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012
```

### Artifactory Configuration

```bash
# Required environment variables
export ARTIFACTORY_URL=https://artifactory.company.com/artifactory
export ARTIFACTORY_REPO=xyz-migration-release
export ARTIFACTORY_USER=your-username
export ARTIFACTORY_API_KEY=your-api-key
```

## Project Structure

```
XYZ migration project/
├── src/app/                    # Application source code
│   ├── lambdas/               # Lambda handler functions
│   ├── services/              # Business logic
│   ├── repositories/          # Data access layer
│   └── utils/                 # Utilities
├── config/                    # Configuration files (.ini)
├── tests/                     # Test suites
├── scripts/                   # Build scripts
│   ├── build_lambda.sh       # Lambda packaging
│   └── upload_artifactory.sh # Artifactory upload
├── dist/                      # Build artifacts (generated)
├── pyproject.toml            # Python packaging metadata
├── Makefile                  # Build automation
└── BUILD.md                  # This document
```

## Building Lambda Packages

### Quick Build

```bash
# Using Makefile (recommended)
make build-lambda

# Or directly
./scripts/build_lambda.sh
```

### Build Process

The build script performs the following steps:

1. **Cleans previous builds**: Removes `build/` and `dist/` directories
2. **Installs dependencies**: Installs boto3, pydantic, psycopg2-binary to temporary directory
3. **Packages Lambda functions**: Creates individual .zip files for each Lambda:
   - `ingestion_lambda.zip` (~16MB)
   - `validation_lambda.zip` (~17MB)
   - `transform_lambda.zip` (~17MB)
   - `load_lambda.zip` (~16MB)
   - `dq_lambda.zip` (~17MB)
   - `orchestration_lambda.zip` (~17MB)
4. **Creates Lambda layer**: Packages shared dependencies into `lambda-layer-dependencies.zip` (~18MB)

### Package Contents

Each Lambda package contains:
- Application code from `src/app/`
- Configuration files from `config/`
- Lambda-specific handler from `src/app/lambdas/`
- Dependencies (boto3, pydantic, psycopg2-binary, etc.)

### Build Output

```
dist/
├── dq_lambda.zip
├── ingestion_lambda.zip
├── lambda-layer-dependencies.zip
├── load_lambda.zip
├── orchestration_lambda.zip
├── transform_lambda.zip
└── validation_lambda.zip
```

## Artifactory Upload

### Upload Lambda Packages

```bash
# Set Artifactory credentials (required)
export ARTIFACTORY_URL=https://artifactory.company.com/artifactory
export ARTIFACTORY_REPO=xyz-migration-release
export ARTIFACTORY_USER=your-username
export ARTIFACTORY_API_KEY=your-api-key

# Upload all packages
./scripts/upload_artifactory.sh
```

### Upload Process

The upload script:
1. Validates environment variables
2. Checks for required packages in `dist/`
3. Extracts version from `pyproject.toml`
4. Collects Git metadata (commit, branch)
5. Uploads each package with properties:
   - `version`: Package version (e.g., "0.1.0")
   - `build.timestamp`: Build timestamp (YYYYMMDDHHMMSS)
   - `vcs.revision`: Git commit hash
   - `vcs.branch`: Git branch name
6. Generates SHA1 and MD5 checksums
7. Creates and uploads build info JSON

### Artifactory Path Structure

```
artifactory/
└── xyz-migration-release/
    └── xyz-migration/
        └── 0.1.0/
            ├── ingestion_lambda.zip
            ├── validation_lambda.zip
            ├── transform_lambda.zip
            ├── load_lambda.zip
            ├── dq_lambda.zip
            ├── orchestration_lambda.zip
            ├── lambda-layer-dependencies.zip
            └── build-info.json
```

### Download from Artifactory

```bash
# Download specific package
curl -u $ARTIFACTORY_USER:$ARTIFACTORY_API_KEY \
  ${ARTIFACTORY_URL}/${ARTIFACTORY_REPO}/xyz-migration/0.1.0/ingestion_lambda.zip \
  -O

# Download with version variable
VERSION=0.1.0
curl -u $ARTIFACTORY_USER:$ARTIFACTORY_API_KEY \
  ${ARTIFACTORY_URL}/${ARTIFACTORY_REPO}/xyz-migration/${VERSION}/transform_lambda.zip \
  -O
```

## AWS Lambda Deployment

### Deploy Individual Lambda

```bash
# Deploy ingestion Lambda
aws lambda update-function-code \
  --function-name xyz-ingestion-lambda \
  --zip-file fileb://dist/ingestion_lambda.zip

# Deploy validation Lambda
aws lambda update-function-code \
  --function-name xyz-validation-lambda \
  --zip-file fileb://dist/validation_lambda.zip
```

### Deploy All Lambdas

```bash
# Using Makefile
make deploy-lambda

# Or loop through all
for lambda in ingestion validation transform load dq orchestration; do
  aws lambda update-function-code \
    --function-name xyz-${lambda}-lambda \
    --zip-file fileb://dist/${lambda}_lambda.zip
done
```

### Deploy Lambda Layer

```bash
# Publish new layer version
aws lambda publish-layer-version \
  --layer-name xyz-migration-dependencies \
  --zip-file fileb://dist/lambda-layer-dependencies.zip \
  --compatible-runtimes python3.10 python3.11 python3.12

# Get layer ARN from output
LAYER_ARN="arn:aws:lambda:us-east-1:123456789012:layer:xyz-migration-dependencies:1"

# Update Lambda to use layer
aws lambda update-function-configuration \
  --function-name xyz-ingestion-lambda \
  --layers $LAYER_ARN
```

### Environment-Specific Deployment

```bash
# Set environment in Lambda configuration
aws lambda update-function-configuration \
  --function-name xyz-ingestion-lambda \
  --environment "Variables={ENV=prod,LOG_LEVEL=INFO}"

# Deploy with Terraform (if using IaC)
terraform apply -var="environment=prod" -var="lambda_version=0.1.0"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main, staging, dev]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: make install-dev
      
      - name: Run tests
        run: make test-cov
      
      - name: Run quality checks
        run: make quality
      
      - name: Build Lambda packages
        run: make build-lambda
      
      - name: Upload to Artifactory
        env:
          ARTIFACTORY_URL: ${{ secrets.ARTIFACTORY_URL }}
          ARTIFACTORY_REPO: ${{ secrets.ARTIFACTORY_REPO }}
          ARTIFACTORY_USER: ${{ secrets.ARTIFACTORY_USER }}
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
        run: ./scripts/upload_artifactory.sh
      
      - name: Deploy to AWS Lambda
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
        run: make deploy-lambda
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    environment {
        ARTIFACTORY_URL = credentials('artifactory-url')
        ARTIFACTORY_REPO = 'xyz-migration-release'
        ARTIFACTORY_USER = credentials('artifactory-user')
        ARTIFACTORY_API_KEY = credentials('artifactory-api-key')
        AWS_REGION = 'us-east-1'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'make install-dev'
            }
        }
        
        stage('Test') {
            steps {
                sh 'make test-cov'
            }
        }
        
        stage('Quality') {
            steps {
                sh 'make quality'
            }
        }
        
        stage('Build') {
            steps {
                sh 'make build-lambda'
            }
        }
        
        stage('Upload Artifactory') {
            steps {
                sh './scripts/upload_artifactory.sh'
            }
        }
        
        stage('Deploy Lambda') {
            when {
                branch 'main'
            }
            steps {
                sh 'make deploy-lambda'
            }
        }
    }
    
    post {
        always {
            junit 'test-results/*.xml'
            publishHTML([reportDir: 'htmlcov', reportFiles: 'index.html', reportName: 'Coverage Report'])
        }
    }
}
```

## Makefile Commands

### Development

```bash
make install          # Install production dependencies
make install-dev      # Install development dependencies
make dev-setup        # Complete dev environment setup
```

### Testing

```bash
make test             # Run unit tests
make test-cov         # Run tests with coverage
make test-integration # Run integration tests
make quick-test       # Fast parallel test run
make watch-test       # Watch mode for TDD
```

### Code Quality

```bash
make format           # Format code (black + isort)
make format-check     # Check formatting
make lint             # Run flake8 linting
make typecheck        # Run mypy type checking
make quality          # Run all quality checks
```

### Build & Deploy

```bash
make clean            # Remove build artifacts
make build-lambda     # Build Lambda packages
make build-wheel      # Build Python wheel
make upload-artifactory  # Upload to Artifactory
make deploy-lambda    # Deploy to AWS Lambda
make ci               # Run full CI pipeline
```

### Help

```bash
make help             # Show all available commands
```

## Troubleshooting

### Build Failures

**Problem**: Dependencies conflict during build
```
ERROR: pip's dependency resolver does not currently take into account...
```

**Solution**: These are warnings about conda environment conflicts, not build errors. The Lambda packages are isolated and won't have these conflicts.

---

**Problem**: `psycopg2-binary` installation fails
```
ERROR: Could not build wheels for psycopg2-binary
```

**Solution**: Ensure PostgreSQL development libraries are installed:
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install libpq-dev

# Or use pre-built binary
pip install psycopg2-binary --no-binary :all:
```

### Deployment Failures

**Problem**: Lambda deployment timeout
```
An error occurred (RequestTimeout) when calling the UpdateFunctionCode operation
```

**Solution**: Lambda package is too large. Use Lambda layers:
```bash
# Create layer with dependencies only
aws lambda publish-layer-version \
  --layer-name xyz-dependencies \
  --zip-file fileb://dist/lambda-layer-dependencies.zip

# Update Lambda configuration to use layer
aws lambda update-function-configuration \
  --function-name xyz-ingestion-lambda \
  --layers arn:aws:lambda:region:account:layer:xyz-dependencies:1
```

---

**Problem**: Lambda cold start timeout
```
Task timed out after 3.00 seconds
```

**Solution**: Increase Lambda timeout and memory:
```bash
aws lambda update-function-configuration \
  --function-name xyz-ingestion-lambda \
  --timeout 30 \
  --memory-size 512
```

### Artifactory Failures

**Problem**: Authentication failure
```
✗ Failed to upload (HTTP 401)
```

**Solution**: Verify credentials:
```bash
# Test Artifactory connection
curl -u $ARTIFACTORY_USER:$ARTIFACTORY_API_KEY \
  ${ARTIFACTORY_URL}/api/system/ping

# Regenerate API key if needed
```

---

**Problem**: Repository not found
```
✗ Failed to upload (HTTP 404)
```

**Solution**: Verify repository exists and user has write permissions:
```bash
# List repositories
curl -u $ARTIFACTORY_USER:$ARTIFACTORY_API_KEY \
  ${ARTIFACTORY_URL}/api/repositories
```

### Test Failures

**Problem**: Tests fail with import errors
```
ModuleNotFoundError: No module named 'app'
```

**Solution**: Install package in editable mode:
```bash
pip install -e .
```

---

**Problem**: Config tests fail with missing .ini files
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/base.ini'
```

**Solution**: Ensure running tests from project root:
```bash
cd "/Users/avishma/Desktop/XYZ migration project"
pytest tests/unit
```

## Version Management

### Update Version

Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Increment version
```

### Create Release Tag

```bash
# Tag release
git tag -a v0.2.0 -m "Release v0.2.0: Add ConfigParser support"

# Push tag
git push origin v0.2.0
```

### Semantic Versioning

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

## Best Practices

1. **Always run tests before building**: `make test`
2. **Use consistent environment variables**: Store in `.env` file (gitignored)
3. **Tag releases**: Use semantic versioning
4. **Document changes**: Update CHANGELOG.md
5. **Review Lambda logs**: Check CloudWatch after deployment
6. **Monitor costs**: Lambda invocations and storage
7. **Use Lambda layers**: For large dependencies (>50MB)
8. **Enable X-Ray**: For distributed tracing
9. **Set up alarms**: CloudWatch alarms for errors
10. **Rotate credentials**: API keys and IAM roles regularly

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [JFrog Artifactory REST API](https://www.jfrog.com/confluence/display/JFROG/Artifactory+REST+API)
- [Python Packaging Guide](https://packaging.python.org/)
- [GitHub Actions for Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)

## Support

For issues or questions:
- **Internal**: Contact Data Engineering team
- **GitHub Issues**: [Create an issue](https://github.com/Cherish0308/XYZ_Migration/issues)
- **Slack**: #xyz-migration channel
