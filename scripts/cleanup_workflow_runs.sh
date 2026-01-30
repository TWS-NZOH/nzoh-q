#!/bin/bash

# Script to delete old GitHub Actions workflow runs
# Keeps only the specified runs:
#   - Build Windows Executable #67
#   - Create Release #5
#   - Build Windows Executable #66

REPO="TWS-NZOH/Q"
API_BASE="https://api.github.com/repos/$REPO"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if token is provided
if [ -z "$GITHUB_TOKEN" ]; then
    # Try to get credentials from git credential helper (e.g., macOS keychain)
    echo -e "${YELLOW}GitHub token not found in environment. Trying git credentials...${NC}"
    
    GIT_CREDS=$(echo "protocol=https
host=github.com
" | git credential fill 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$GIT_CREDS" ]; then
        # Extract password (which is typically the token when using HTTPS)
        GITHUB_TOKEN=$(echo "$GIT_CREDS" | grep "^password=" | cut -d'=' -f2)
        GIT_USERNAME=$(echo "$GIT_CREDS" | grep "^username=" | cut -d'=' -f2)
        
        if [ -n "$GITHUB_TOKEN" ]; then
            echo -e "${GREEN}Using credentials from git (username: $GIT_USERNAME)${NC}"
        fi
    fi
fi

# If still no token, prompt user
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}GitHub token not found in environment or git credentials.${NC}"
    echo "Please provide your GitHub Personal Access Token:"
    echo "1. Create one at: https://github.com/settings/tokens"
    echo "2. Required permissions: repo, workflow"
    echo ""
    read -sp "Enter your GitHub token: " GITHUB_TOKEN
    echo ""
    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${RED}Error: GitHub token is required${NC}"
        exit 1
    fi
fi

# Runs to keep: format is "workflow_name|run_number"
# This ensures we keep the correct workflow, not just any workflow with that run number
KEEP_RUNS=(
    "Build Windows Executable|67"
    "Create Release|5"
    "Build Windows Executable|66"
)

echo -e "${GREEN}Fetching workflow runs for $REPO...${NC}"

# Get all workflow runs
RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "$API_BASE/actions/runs?per_page=100")

# Check if API call was successful
if echo "$RESPONSE" | grep -q '"message"'; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${RED}Error: $ERROR_MSG${NC}"
    exit 1
fi

# Count total runs
TOTAL_RUNS=$(echo "$RESPONSE" | grep -o '"total_count":[0-9]*' | head -1 | cut -d':' -f2)
echo "Total workflow runs found: $TOTAL_RUNS"
echo ""

# Parse and delete runs
DELETED=0
KEPT=0

# Save runs to a temp file for processing
TEMP_FILE=$(mktemp)
echo "$RESPONSE" > "$TEMP_FILE"

# Use jq if available, otherwise use grep/sed
if command -v jq &> /dev/null; then
    # Use jq for better JSON parsing
    jq -r '.workflow_runs[] | "\(.id)|\(.run_number)|\(.name)|\(.head_branch)"' "$TEMP_FILE" | while IFS='|' read -r RUN_ID RUN_NUMBER WORKFLOW_NAME BRANCH; do
        # Check if this run should be kept (match both workflow name AND run number)
        KEEP=false
        for keep_entry in "${KEEP_RUNS[@]}"; do
            KEEP_NAME=$(echo "$keep_entry" | cut -d'|' -f1)
            KEEP_NUM=$(echo "$keep_entry" | cut -d'|' -f2)
            if [ "$WORKFLOW_NAME" == "$KEEP_NAME" ] && [ "$RUN_NUMBER" == "$KEEP_NUM" ]; then
                KEEP=true
                break
            fi
        done
        
        if [ "$KEEP" = true ]; then
            echo -e "${GREEN}✓ Keeping${NC} Workflow: $WORKFLOW_NAME #$RUN_NUMBER (ID: $RUN_ID) - Branch: $BRANCH"
            KEPT=$((KEPT + 1))
        else
            echo -e "${YELLOW}Deleting${NC} Workflow: $WORKFLOW_NAME #$RUN_NUMBER (ID: $RUN_ID) - Branch: $BRANCH"
            
            HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE \
                -H "Authorization: token $GITHUB_TOKEN" \
                -H "Accept: application/vnd.github.v3+json" \
                "$API_BASE/actions/runs/$RUN_ID")
            
            if [ "$HTTP_CODE" == "204" ]; then
                echo -e "  ${GREEN}✓ Deleted successfully${NC}"
                DELETED=$((DELETED + 1))
            else
                echo -e "  ${RED}✗ Failed to delete (HTTP $HTTP_CODE)${NC}"
            fi
        fi
    done
else
    # Fallback to grep/sed parsing
    echo "$RESPONSE" | grep -o '"id":[0-9]*,"name":"[^"]*","head_branch":"[^"]*","run_number":[0-9]*' | while IFS= read -r line; do
        RUN_ID=$(echo "$line" | grep -o '"id":[0-9]*' | cut -d':' -f2)
        RUN_NUMBER=$(echo "$line" | grep -o '"run_number":[0-9]*' | cut -d':' -f2)
        WORKFLOW_NAME=$(echo "$line" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        BRANCH=$(echo "$line" | grep -o '"head_branch":"[^"]*"' | cut -d'"' -f4)
        
        # Check if this run should be kept (match both workflow name AND run number)
        KEEP=false
        for keep_entry in "${KEEP_RUNS[@]}"; do
            KEEP_NAME=$(echo "$keep_entry" | cut -d'|' -f1)
            KEEP_NUM=$(echo "$keep_entry" | cut -d'|' -f2)
            if [ "$WORKFLOW_NAME" == "$KEEP_NAME" ] && [ "$RUN_NUMBER" == "$KEEP_NUM" ]; then
                KEEP=true
                break
            fi
        done
        
        if [ "$KEEP" = true ]; then
            echo -e "${GREEN}✓ Keeping${NC} Workflow: $WORKFLOW_NAME #$RUN_NUMBER (ID: $RUN_ID) - Branch: $BRANCH"
            KEPT=$((KEPT + 1))
        else
            echo -e "${YELLOW}Deleting${NC} Workflow: $WORKFLOW_NAME #$RUN_NUMBER (ID: $RUN_ID) - Branch: $BRANCH"
            
            HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE \
                -H "Authorization: token $GITHUB_TOKEN" \
                -H "Accept: application/vnd.github.v3+json" \
                "$API_BASE/actions/runs/$RUN_ID")
            
            if [ "$HTTP_CODE" == "204" ]; then
                echo -e "  ${GREEN}✓ Deleted successfully${NC}"
                DELETED=$((DELETED + 1))
            else
                echo -e "  ${RED}✗ Failed to delete (HTTP $HTTP_CODE)${NC}"
            fi
        fi
    done
fi

rm -f "$TEMP_FILE"

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"
echo "Runs kept: $KEPT"
echo "Runs deleted: $DELETED"

