#!/usr/bin/env bash
# Resolve as duas configuracoes sem falar com o daemon e sem ler .env real.
set -euo pipefail
raiz=$(cd "$(dirname "$0")/../.." && pwd)
temporario=$(mktemp -d)
trap 'rm -rf "$temporario"' EXIT
cp "$raiz"/compose.{ambientes,desenvolvimento,producao}.yaml "$temporario/"
cat > "$temporario/.env" <<'FIM'
SECRET_KEY=descartavel
DB_USER=almox
DB_PASSWORD=teste
SAEP_USER=nao-pode-vazar
SAEP_PASS=nao-pode-vazar
TELEGRAM_TOKEN=nao-pode-vazar
TELEGRAM_CHAT_ID=nao-pode-vazar
LANCAMENTO_REAL=1
FIM
echo 'MARIADB_ROOT_PASSWORD=teste' > "$temporario/.env.banco"
for ambiente in desenvolvimento producao; do
  PROJETO_COMPOSE="teste-$ambiente" AMBIENTE_DEPLOY="$ambiente" \
    REVISAO_APP=abc123 IMAGEM_APP="teste-$ambiente:abc123" \
    docker compose --project-directory "$temporario" --env-file "$temporario/.env" \
    -f "$temporario/compose.ambientes.yaml" -f "$temporario/compose.$ambiente.yaml" \
    --profile '*' config --format json > "$temporario/$ambiente.json"
done
python3 - "$temporario" <<'PY'
import json
import sys
from pathlib import Path

pasta = Path(sys.argv[1])
dev = json.loads((pasta / 'desenvolvimento.json').read_text())
prod = json.loads((pasta / 'producao.json').read_text())
assert prod['name'] != dev['name']
assert prod['volumes']['banco-dados']['name'] != dev['volumes']['banco-dados']['name']
assert prod['volumes']['perfil-navegador']['name'] != dev['volumes']['perfil-navegador']['name']
for nome in ('web', 'agendador'):
    d, p = dev['services'][nome], prod['services'][nome]
    assert d['image'] != p['image']
    assert 'build' not in p
    assert d['environment']['LANCAMENTO_REAL'] == '0'
    for chave in ('SAEP_USER', 'SAEP_PASS', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'):
        assert d['environment'][chave] == ''
    assert d['environment']['DB_HOST'] == p['environment']['DB_HOST'] == 'banco'
    assert 'MARIADB_ROOT_PASSWORD' not in d['environment']
assert 'agendamento' in prod['services']['agendador']['profiles']
assert prod['services']['web']['ports'][0]['host_ip'] == '127.0.0.1'
assert dev['services']['web']['ports'][0]['host_ip'] == '127.0.0.1'
assert not prod['services']['banco'].get('ports')
print('PASS: projetos, imagens, volumes, credenciais e portas isolados no Compose resolvido.')
PY
