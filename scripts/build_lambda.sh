#!/bin/bash
# Lambda packaging script for AWS deployment
# Creates deployment-ready .zip packages for each Lambda function

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"
SRC_DIR="${PROJECT_ROOT}/src"
CONFIG_DIR="${PROJECT_ROOT}/config"

# Lambda functions to package
LAMBDAS=(
    "ingestion_lambda"
    "validation_lambda"
    "transform_lambda"
    "load_lambda"
    "dq_lambda"
    "orchestration_lambda"
)

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  XYZ Migration Lambda Packager         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Clean previous builds
echo -e "${YELLOW}→${NC} Cleaning previous builds..."
rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

# Install dependencies to temp directory
echo -e "${YELLOW}→${NC} Installing dependencies..."
TEMP_DEPS="${BUILD_DIR}/python"
mkdir -p "${TEMP_DEPS}"
pip install --quiet --target "${TEMP_DEPS}" \
    boto3 \
    botocore \
    pydantic \
    pydantic-settings \
    psycopg2-binary

# Package each Lambda function
for lambda in "${LAMBDAS[@]}"; do
    echo -e "${YELLOW}→${NC} Packaging ${lambda}..."
    
    LAMBDA_BUILD="${BUILD_DIR}/${lambda}"
    mkdir -p "${LAMBDA_BUILD}"
    
    # Copy dependencies
    cp -r "${TEMP_DEPS}"/* "${LAMBDA_BUILD}/"
    
    # Copy application code
    cp -r "${SRC_DIR}/app" "${LAMBDA_BUILD}/"
    
    # Copy config files
    cp -r "${CONFIG_DIR}" "${LAMBDA_BUILD}/"
    
    # Create zip package
    cd "${LAMBDA_BUILD}"
    zip -q -r "${DIST_DIR}/${lambda}.zip" . \
        -x "*.pyc" \
        -x "*__pycache__*" \
        -x "*.git*"
    
    # Get package size
    SIZE=$(du -h "${DIST_DIR}/${lambda}.zip" | cut -f1)
    echo -e "  ${GREEN}✓${NC} Created ${lambda}.zip (${SIZE})"
done

cd "${PROJECT_ROOT}"

# Create a shared layer for common dependencies
echo -e "${YELLOW}→${NC} Creating Lambda layer for shared dependencies..."
LAYER_BUILD="${BUILD_DIR}/layer"
mkdir -p "${LAYER_BUILD}/python"
cp -r "${TEMP_DEPS}"/* "${LAYER_BUILD}/python/"

cd "${LAYER_BUILD}"
zip -q -r "${DIST_DIR}/lambda-layer-dependencies.zip" python/
LAYER_SIZE=$(du -h "${DIST_DIR}/lambda-layer-dependencies.zip" | cut -f1)
echo -e "  ${GREEN}✓${NC} Created lambda-layer-dependencies.zip (${LAYER_SIZE})"

cd "${PROJECT_ROOT}"

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Build Complete                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Lambda packages created in: ${DIST_DIR}"
echo ""
echo "Deploy commands:"
for lambda in "${LAMBDAS[@]}"; do
    echo "  aws lambda update-function-code \\"
    echo "    --function-name ${lambda} \\"
    echo "    --zip-file fileb://dist/${lambda}.zip"
    echo ""
done

echo "Layer deployment:"
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name xyz-migration-dependencies \\"
echo "    --zip-file fileb://dist/lambda-layer-dependencies.zip \\"
echo "    --compatible-runtimes python3.10 python3.11 python3.12"
echo ""
