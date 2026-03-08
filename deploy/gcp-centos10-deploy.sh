#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   REPO_URL="https://github.com/<you>/<repo>.git" bash deploy/gcp-centos10-deploy.sh
#
# Optional env vars:
#   BRANCH=main
#   DEPLOY_ROOT=/opt/md2docx
#   APP_SUBDIR=project/md2docx
#   SERVICE_NAME=md2docx-web
#   EXPOSE_PORT=8080

REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/md2docx}"
APP_SUBDIR="${APP_SUBDIR:-project/md2docx}"
SERVICE_NAME="${SERVICE_NAME:-md2docx-web}"
EXPOSE_PORT="${EXPOSE_PORT:-8080}"

if [[ -z "${REPO_URL}" ]]; then
  echo "ERROR: REPO_URL is required."
  echo "Example: REPO_URL='https://github.com/<you>/<repo>.git' bash deploy/gcp-centos10-deploy.sh"
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

log() {
  echo "[md2docx-deploy] $*"
}

install_system_deps() {
  log "Installing system dependencies..."
  ${SUDO} dnf -y install dnf-plugins-core git curl ca-certificates

  if [[ ! -f /etc/yum.repos.d/docker-ce.repo ]]; then
    log "Adding Docker CE repo..."
    ${SUDO} dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  fi

  ${SUDO} dnf makecache -y
  ${SUDO} dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  ${SUDO} systemctl enable --now docker
}

configure_firewall() {
  if command -v firewall-cmd >/dev/null 2>&1 && ${SUDO} systemctl is-active --quiet firewalld; then
    log "Opening firewall port ${EXPOSE_PORT}/tcp..."
    ${SUDO} firewall-cmd --permanent --add-port="${EXPOSE_PORT}"/tcp
    ${SUDO} firewall-cmd --reload
  else
    log "firewalld not active, skipping firewall configuration."
  fi
}

sync_repo() {
  if [[ -d "${DEPLOY_ROOT}/.git" ]]; then
    log "Updating existing repository at ${DEPLOY_ROOT}..."
    git -C "${DEPLOY_ROOT}" fetch --all --prune
    git -C "${DEPLOY_ROOT}" checkout "${BRANCH}"
    git -C "${DEPLOY_ROOT}" pull --ff-only origin "${BRANCH}"
  else
    log "Cloning repository..."
    ${SUDO} mkdir -p "$(dirname "${DEPLOY_ROOT}")"
    ${SUDO} rm -rf "${DEPLOY_ROOT}"
    git clone --branch "${BRANCH}" "${REPO_URL}" "${DEPLOY_ROOT}"
  fi
}

deploy_service() {
  APP_DIR="${DEPLOY_ROOT}/${APP_SUBDIR}"
  if [[ ! -f "${APP_DIR}/docker-compose.yml" ]]; then
    echo "ERROR: docker-compose.yml not found: ${APP_DIR}/docker-compose.yml"
    exit 1
  fi

  log "Deploying service from ${APP_DIR}..."
  cd "${APP_DIR}"
  ${SUDO} docker compose up -d --build "${SERVICE_NAME}"
  ${SUDO} docker compose ps
}

print_summary() {
  local host_ip
  host_ip="$(hostname -I | awk '{print $1}')"
  log "Deployment complete."
  log "Try opening: http://${host_ip}:${EXPOSE_PORT}/"
  log "Health check: curl http://127.0.0.1:${EXPOSE_PORT}/health"
}

install_system_deps
configure_firewall
sync_repo
deploy_service
print_summary

