#!/usr/bin/env bash
set -euo pipefail

cd /workspace
mkdir -p resultados build

echo "[1/3] Detectando flags de compilação do ns-3..."
PC_PKGS=$(pkg-config --list-all 2>/dev/null | awk '{print $1}' | grep -E '^(lib)?ns3.*(core|network|internet|point-to-point|applications|flow-monitor|traffic-control)$' | sort -u || true)

if [ -n "$PC_PKGS" ]; then
    echo "Pacotes pkg-config encontrados:"
    echo "$PC_PKGS"
    CFLAGS=$(pkg-config --cflags $PC_PKGS)
    LIBS=$(pkg-config --libs $PC_PKGS)
else
    echo "Fallback: buscando headers e libs do ns-3 em /usr..."
    INC_DIR=$(find /usr/include -maxdepth 2 -type d -name "ns3*" | head -n 1)
    CFLAGS="-I${INC_DIR} -I/usr/include"
    LIB_LIST=$(find /usr/lib -name "libns3*core*.so*" -o -name "libns3*network*.so*" -o -name "libns3*internet*.so*" -o -name "libns3*point-to-point*.so*" -o -name "libns3*applications*.so*" -o -name "libns3*flow-monitor*.so*" -o -name "libns3*traffic-control*.so*" | grep -E '\.so$' | sort -u)
    LIBS="$LIB_LIST"
fi

echo "CFLAGS=$CFLAGS"

echo "[2/3] Compilando custom-tcp-app.cc e simulacao_dumbbell.cc..."
g++ -std=c++20 -O2 -g -Wall \
    src/custom-tcp-app.cc \
    src/simulacao_dumbbell.cc \
    $CFLAGS $LIBS \
    -o build/simulacao_dumbbell

echo "[3/3] Executando simulação NS-3 (Gargalo 100Mbps, 10ms, DropTail)..."
./build/simulacao_dumbbell --bottleneckRate=100Mbps --bottleneckDelay=10ms --queueSize=100p --outputDir=resultados

echo "[OK] Simulação concluída! Arquivos salvos em /workspace/resultados/"
ls -lh resultados/
