#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# 一键部署脚本 - 前端静态文件 + Nginx
#
# 用法：
#   ./scripts/deploy.sh              # 完整部署（拉取+构建+部署）
#   ./scripts/deploy.sh --build-only # 仅构建+部署（不拉取代码）
#   ./scripts/deploy.sh --pull-only  # 仅拉取代码（不构建）
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
DIST_DIR="${FRONTEND_DIR}/dist"
WWW_DIR="/www/wwwroot/agently.top"
NGINX_CONF="/www/server/panel/vhost/nginx/agently.top.conf"

BUILD_ONLY=false
PULL_ONLY=false

for arg in "$@"; do
  case $arg in
    --build-only) BUILD_ONLY=true ;;
    --pull-only)  PULL_ONLY=true ;;
    -h|--help)
      echo "用法: $0 [--build-only] [--pull-only]"
      echo "  --build-only  仅构建+部署（不拉取代码）"
      echo "  --pull-only   仅拉取代码（不构建）"
      exit 0
      ;;
  esac
done

echo "========================================="
echo "  部署 agently.top"
echo "========================================="

# --- 1. 拉取最新代码 ---
if [ "$PULL_ONLY" = false ]; then
  echo ""
  echo "[1/4] 拉取最新代码..."
  cd "${ROOT_DIR}"
  git pull origin master
  echo "  ✓ 代码已更新"
fi

# --- 2. 安装前端依赖 ---
if [ "$BUILD_ONLY" = true ] || [ "$PULL_ONLY" = false ]; then
  echo ""
  echo "[2/4] 检查前端依赖..."
  cd "${FRONTEND_DIR}"
  if [ ! -d "node_modules" ]; then
    echo "  安装 npm 依赖..."
    npm install
  else
    echo "  ✓ node_modules 已存在"
  fi

  # --- 3. 构建前端 ---
  echo ""
  echo "[3/4] 构建前端..."
  npx vue-cli-service build
  echo "  ✓ 构建完成"

  # --- 4. 部署静态文件 ---
  echo ""
  echo "[4/4] 部署静态文件到 Nginx..."
  cp -r "${DIST_DIR}"/* "${WWW_DIR}/"
  nginx -s reload 2>/dev/null || echo "  ⚠ Nginx 重载失败，请手动执行: nginx -s reload"
  echo "  ✓ 部署完成"
fi

echo ""
echo "========================================="
echo "  部署成功！访问 https://agently.top/"
echo "========================================="
