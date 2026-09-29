#!/bin/bash
# Duplo clique no Finder: agenda as rotinas automaticas neste Mac (launchd).
# ATENCAO: so na UNICA maquina do escritorio que roda as rotinas (senao o cliente
# recebe mensagem em dobro). O script pergunta antes de agendar.
# Na primeira vez o macOS pode bloquear: botao direito no arquivo > Abrir > Abrir.
cd "$(dirname "$0")" || exit 1
/bin/bash ./agendar_tarefas_mac.sh "$@"
echo
read -n 1 -s -r -p "Aperte qualquer tecla para fechar esta janela."
echo
