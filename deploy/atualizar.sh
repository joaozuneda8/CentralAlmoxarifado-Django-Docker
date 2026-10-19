#!/usr/bin/env bash
# Legado bloqueado: o antigo git pull + compose podia atualizar o ambiente errado.
set -eu
echo 'Atualizador legado bloqueado. Consulte deploy/AMBIENTES.md e use deploy/atualizar.ps1 com ambiente explicito.' >&2
exit 1
