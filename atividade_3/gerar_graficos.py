#!/usr/bin/env python3
"""
Gera gráficos a partir dos CSVs produzidos pela simulação NS-3 da Atividade 3.
Uso:
    uv run --with matplotlib --with pandas python3 gerar_graficos.py
"""

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RES_DIR = BASE_DIR / "resultados"
IMG_DIR = BASE_DIR / "imagens"

plt.style.use("seaborn-v0_8-whitegrid")


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    df_tp = pd.read_csv(RES_DIR / "throughput_series.csv")
    df_cwnd_bulk = pd.read_csv(RES_DIR / "cwnd_bulk.csv")
    df_cwnd_custom = pd.read_csv(RES_DIR / "cwnd_custom.csv")
    df_rtt_bulk = pd.read_csv(RES_DIR / "rtt_bulk.csv")
    df_rtt_custom = pd.read_csv(RES_DIR / "rtt_custom.csv")

    fig, axes = plt.subplots(3, 1, figsize=(11, 10.5), sharex=True)

    # 1. Vazão (Throughput)
    axes[0].plot(df_tp["time_s"], df_tp["udp_mbps"], label="Fluxo 1: UDP (3 Mbps)", color="#2ca02c", linewidth=1.6)
    axes[0].plot(df_tp["time_s"], df_tp["bulk_mbps"], label="Fluxo 2: TCP Bulk", color="#1f77b4", linewidth=1.6)
    axes[0].plot(df_tp["time_s"], df_tp["custom_mbps"], label="Fluxo 3: TCP Custom (50 KB / 2s)", color="#d62728", linewidth=1.6)
    axes[0].set_ylabel("Vazão (Mbps)")
    axes[0].set_title("Vazão Instantânea dos Três Fluxos (Gargalo 100 Mbps, 10 ms, DropTail)", fontsize=12, fontweight="bold")
    axes[0].legend(loc="upper right")

    # 2. Janela de Congestionamento (cwnd)
    axes[1].plot(df_cwnd_bulk["time_s"], df_cwnd_bulk["cwnd_bytes"] / 1024.0, label="Fluxo 2: TCP Bulk", color="#1f77b4", linewidth=1.4)
    axes[1].plot(df_cwnd_custom["time_s"], df_cwnd_custom["cwnd_bytes"] / 1024.0, label="Fluxo 3: TCP Custom", color="#d62728", linewidth=1.4)
    axes[1].set_ylabel("cwnd (KB)")
    axes[1].set_title("Evolução da Janela de Congestionamento (cwnd)", fontsize=12, fontweight="bold")
    axes[1].legend(loc="upper right")

    # 3. RTT
    axes[2].plot(df_rtt_bulk["time_s"], df_rtt_bulk["rtt_ms"], label="Fluxo 2: TCP Bulk", color="#1f77b4", alpha=0.85, linewidth=1.2)
    axes[2].plot(df_rtt_custom["time_s"], df_rtt_custom["rtt_ms"], label="Fluxo 3: TCP Custom", color="#d62728", alpha=0.85, linewidth=1.2)
    axes[2].set_xlabel("Tempo de Simulação (s)")
    axes[2].set_ylabel("RTT (ms)")
    axes[2].set_title("Evolução do RTT dos Fluxos TCP", fontsize=12, fontweight="bold")
    axes[2].legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(IMG_DIR / "metricas_ns3.png", dpi=200)
    plt.close(fig)
    print(f"[SUCESSO] Gráfico salvo em {IMG_DIR / 'metricas_ns3.png'}")


if __name__ == "__main__":
    main()
