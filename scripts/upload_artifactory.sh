#!/bin/bash

# XYZ Migration - Artifactory Upload Script
# Uploads Lambda packages to JFrog Artifactory for version management

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
VERSION=$(grep -E '^version = ' "${PROJECT_ROOT}/pyproject.toml" | cut -d'"' -f2)

# Artifactory Configuration (set these environment variables before running)
: "${ARTIFACTORY_URL:?Error: ARTIFACTORY_URL environment variable not set}"
: "${ARTIFACTORY_REPO:?Error: ARTIFACTORY_REPO environment variable not set}"
: "${ARTIFACTORY_USER:?Error: ARTIFACTORY_USER environment variable not set}"
: "${ARTIFACTORY_API_KEY:?Error: ARTIFACTORY_API_KEY environment variable not set}"

# Build metadata
BUILD_TIMESTAMP=$(date -u +"%Y%m%d%H%M%S")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════╗"
echo "║  XYZ Migration Artifactory Uploader   ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}→${NC} Project: xyz-migration"
echo -e "${BLUE}→${NC} Version: ${VERSION}"
echo -e "${BLUE}→${NC} Git Commit: ${GIT_COMMIT}"
echo -e "${BLUE}→${NC} Git Branch: ${GIT_BRANCH}"
echo -e "${BLUE}→${NC} Build Timestamp: ${BUILD_TIMESTAMP}"
echo ""

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}✗${NC} Distribution directory not found: $DIST_DIR"
    echo -e "${YELLOW}→${NC} Run './scripts/build_lambda.sh' first to create packages"
    exit 1
fi

# Check if packages exist
LAMBDA_PACKAGES=(
    "ingestion_lambda.zip"
    "validation_lambda.zip"
    "transform_lambda.zip"
    "load_lambda.zip"
    "dq_lambda.zip"
    "orchestration_lambda.zip"
    "lambda-layer-dependencies.zip"
)

echo -e "${BLUE}→${NC} Checking Lambda packages..."
MISSING_PACKAGES=()
for package in "${LAMBDA_PACKAGES[@]}"; do
    if [ ! -f "${DIST_DIR}/${package}" ]; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${RED}✗${NC} Missing packages:"
    for package in "${MISSING_PACKAGES[@]}"; do
        echo "  - $package"
    done
    echo -e "${YELLOW}→${NC} Run './scripts/build_lambda.sh' to create missing packages"
    exit 1
fi

echo -e "${GREEN}✓${NC} All Lambda packages found"
echo ""

# Function to upload file to Artifactory
upload_to_artifactory() {
    local file_path=$1
    local file_name=$(basename "$file_path")
    local artifact_path="${ARTIFACTORY_REPO}/xyz-migration/${VERSION}/${file_name}"
    local full_url="${ARTIFACTORY_URL}/${artifact_path}"
    
    echo -e "${BLUE}→${NC} Uploading ${file_name}..."
    
    # Upload file with metadata properties
    local properties="version=${VERSION};build.timestamp=${BUILD_TIMESTAMP};vcs.revision=${GIT_COMMIT};vcs.branch=${GIT_BRANCH}"
    
    response=$(curl -u "${ARTIFACTORY_USER}:${ARTIFACTORY_API_KEY}" \
        -X PUT \
        -T "$file_path" \
        -H "X-Checksum-Deploy: true" \
        -H "X-Checksum-Sha1: $(shasum -a 1 "$file_path" | cut -d' ' -f1)" \
        -H "X-Checksum-Md5: $(md5 -q "$file_path")" \
        "${full_url};${properties}" \
        -s -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
        local file_size=$(du -h "$file_path" | cut -f1)
        echo -e "${GREEN}✓${NC} Uploaded ${file_name} (${file_size}) - ${full_url}"
        return 0
    else
        echo -e "${RED}✗${NC} Failed to upload ${file_name} (HTTP ${http_code})"
        echo "$response" | head -n-1
        return 1
    fi
}

# Upload Lambda packages
echo -e "${CYAN}${BOLD}Uploading Lambda Packages:${NC}"
UPLOAD_SUCCESS=0
UPLOAD_FAILED=0

for package in "${LAMBDA_PACKAGES[@]}"; do
    if upload_to_artifactory "${DIST_DIR}/${package}"; then
        ((UPLOAD_SUCCESS++))
    else
        ((UPLOAD_FAILED++))
    fi
done

echo ""

# Upload Python wheel if exists
if ls "${DIST_DIR}"/*.whl 1> /dev/null 2>&1; then
    echo -e "${CYAN}${BOLD}Uploading Python Wheel:${NC}"
    for wheel in "${DIST_DIR}"/*.whl; do
        if upload_to_artifactory "$wheel"; then
            ((UPLOAD_SUCCESS++))
        else
            ((UPLOAD_FAILED++))
        fi
    done
    echo ""
fi

# Create build info JSON
BUILD_INFO_FILE="${DIST_DIR}/build-info.json"
cat > "$BUILD_INFO_FILE" <<EOF
{
  "version": "${VERSION}",
  "name": "xyz-migration",
  "number": "${BUILD_TIMESTAMP}",
  "started": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "vcsRevision": "${GIT_COMMIT}",
  "vcsBranch": "${GIT_BRANCH}",
  "modules": [
    {
      "id": "xyz-migration:${VERSION}",
      "artifacts": [
$(for i in "${!LAMBDA_PACKAGES[@]}"; do
    package="${LAMBDA_PACKAGES[$i]}"
    echo "        {"
    echo "          \"name\": \"${package}\","
    echo "          \"type\": \"zip\""
    if [ $i -lt $((${#LAMBDA_PACKAGES[@]} - 1)) ]; then
        echo "        },"
    else
        echo "        }"
    fi
done)
      ]
    }
  ]
}
EOF

# Upload build info
echo -e "${BLUE}→${NC} Uploading build info..."
if upload_to_artifactory "$BUILD_INFO_FILE"; then
    echo -e "${GREEN}✓${NC} Build info uploaded"
else
    echo -e "${YELLOW}⚠${NC} Build info upload failed (non-critical)"
fi

echo ""
echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════╗"
echo "║  Upload Summary                       ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo -e "${GREEN}✓${NC} Successful: ${UPLOAD_SUCCESS}"
echo -e "${RED}✗${NC} Failed: ${UPLOAD_FAILED}"
echo ""

if [ $UPLOAD_FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ All artifacts uploaded successfully!${NC}"
    echo ""
    echo "Artifactory URL: ${ARTIFACTORY_URL}/${ARTIFACTORY_REPO}/xyz-migration/${VERSION}/"
    echo ""
    echo "To download artifacts:"
    echo "  curl -u \$ARTIFACTORY_USER:\$ARTIFACTORY_API_KEY \\"
    echo "    ${ARTIFACTORY_URL}/${ARTIFACTORY_REPO}/xyz-migration/${VERSION}/ingestion_lambda.zip \\"
    echo "    -O"
    exit 0
else
    echo -e "${RED}${BOLD}✗ Some uploads failed${NC}"
    exit 1
fi
