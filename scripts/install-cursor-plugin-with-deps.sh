#!/usr/bin/env bash
# 将 moon-skills 注册为 Cursor 本地插件，并安装 immune-debug 所需的 superpowers skill。
# 用法见 README「一键安装」。

set -euo pipefail

REPO_URL="${MOON_SKILLS_REPO_URL:-https://github.com/CCharlesMeng/moon-skills.git}"
DEFAULT_CHECKOUT="${XDG_DATA_HOME:-$HOME/.local/share}/moon-skills/checkout"
CHECKOUT_DIR="${MOON_SKILLS_CHECKOUT:-$DEFAULT_CHECKOUT}"
PLUGIN_NAME="${MOON_SKILLS_PLUGIN_NAME:-moon-skills}"
PLUGIN_LINK="${HOME}/.cursor/plugins/local/${PLUGIN_NAME}"

die() {
  echo "error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "未找到命令: $1"
}

require_cmd git
require_cmd npx

mkdir -p "$(dirname "$PLUGIN_LINK")"

if [[ -n "${MOON_SKILLS_CHECKOUT:-}" ]]; then
  [[ -f "${CHECKOUT_DIR}/.cursor-plugin/plugin.json" ]] ||
    die "MOON_SKILLS_CHECKOUT 不是有效插件根目录（缺少 .cursor-plugin/plugin.json）: ${CHECKOUT_DIR}"
else
  if [[ -d "${CHECKOUT_DIR}/.git" ]]; then
    git -C "${CHECKOUT_DIR}" pull --ff-only
  else
    [[ -e "${CHECKOUT_DIR}" ]] &&
      die "目标目录已存在且不是 git 仓库: ${CHECKOUT_DIR}（请删除后重试，或设置 MOON_SKILLS_CHECKOUT）"
    mkdir -p "$(dirname "${CHECKOUT_DIR}")"
    git clone --depth 1 "${REPO_URL}" "${CHECKOUT_DIR}"
  fi
  [[ -f "${CHECKOUT_DIR}/.cursor-plugin/plugin.json" ]] ||
    die "克隆结果缺少 .cursor-plugin/plugin.json: ${CHECKOUT_DIR}"
fi

ln -sfn "${CHECKOUT_DIR}" "${PLUGIN_LINK}"

echo "Cursor 本地插件已就绪: ${PLUGIN_LINK} -> ${CHECKOUT_DIR}"
echo "正在安装 superpowers / systematic-debugging（immune-debug 依赖）..."
npx --yes skills add obra/superpowers --skill systematic-debugging

echo ""
echo "下一步：在 Cursor 中执行「Developer: Reload Window」重新加载窗口，然后在 Settings → Rules 中确认插件已加载。"
