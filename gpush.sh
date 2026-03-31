#!/bin/bash

echo ""
echo "============================================"
echo "     GPUSH - SPX Crypto Quant Lab Backup    "
echo "============================================"
echo ""

# Show current status
echo "========== GIT STATUS =========="
git status
echo ""

echo "========== CHANGED FILES =========="
git diff --stat
echo ""

# Get commit message
read -p "Commit message: " msg

if [ -z "$msg" ]; then
    echo "❌ Commit message cannot be empty."
    exit 1
fi

# Create timestamped tag
tag="dev-$(date +%Y%m%d-%H%M%S)"
echo ""
echo "Using tag: $tag"
echo ""

# Add, commit, and tag
git add .
git commit -m "$msg"
git tag "$tag"

echo ""
echo "Pushing to GitHub..."
echo ""

branch=$(git branch --show-current)

git push origin "$branch"
git push origin "$tag"

echo ""
echo "✅ Done!"
echo "Branch pushed : $branch"
echo "Tag created   : $tag"
echo ""
echo "Repository successfully backed up."
echo ""
