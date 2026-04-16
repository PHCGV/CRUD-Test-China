#!/bin/bash
set -euo pipefail

APP_USER="${APP_USER:-CHINA}"
APP_USER_PASSWORD="${APP_USER_PASSWORD:-}"
DB_CONNECT="${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/XEPDB1"

if [[ -z "${APP_USER_PASSWORD}" ]]; then
  echo "APP_USER_PASSWORD nao definido; abortando inicializacao de schema."
  exit 1
fi

scripts=(
  "/opt/oracle/scripts/setup/010_schema.sql"
  "/opt/oracle/scripts/setup/020_password_reset.sql"
  "/opt/oracle/scripts/setup/030_add_servico_frete.sql"
  "/opt/oracle/scripts/setup/040_drop_modalidade_tb_frete.sql"
)

echo "Aplicando schema e migracoes CityChina para usuario ${APP_USER}..."

for script_path in "${scripts[@]}"; do
  if [[ ! -f "${script_path}" ]]; then
    echo "Arquivo nao encontrado: ${script_path}"
    exit 1
  fi

  echo "Executando ${script_path}"
  sqlplus -s -L "${DB_CONNECT}" <<SQL
WHENEVER SQLERROR EXIT SQL.SQLCODE
@${script_path}
EXIT
SQL
done

echo "Schema e migracoes aplicados com sucesso."
