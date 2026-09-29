#!/bin/bash
# Duplo clique no Finder: abre o Terminal e instala o sistema do Caldeira neste Mac.
# Na primeira vez o macOS pode bloquear (arquivo baixado da internet):
# botao direito no arquivo > Abrir > Abrir.
cd "$(dirname "$0")" || exit 1
/bin/bash ./instalar_mac.sh "$@"
echo
read -n 1 -s -r -p "Aperte qualquer tecla para fechar esta janela."
echo
