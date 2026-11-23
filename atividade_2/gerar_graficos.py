#!/usr/bin/env python3
"""
Script de análise e geração de gráficos da Atividade 2 (TCP CUBIC vs TCP Vegas).
Uso:
    uv run --with matplotlib --with pandas --with numpy python3 gerar_graficos.py
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dados"
RAW_DIR = DATA_DIR / "raw"
IMG_DIR = BASE_DIR / "imagens"
SUMMARY_CSV = DATA_DIR / "resumo_experimentos.csv"

plt.style.use("seaborn-v0_8-whitegrid")
COLORS = {"cubic": "#1f77b4", "vegas": "#d62728"}
LABELS = {"cubic": "TCP CUBIC", "vegas": "TCP Vegas"}


def load_raw_series(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["span"] = df["iend"] - df["istart"]
    # Remove a última linha de resumo (span > 1.0)
    df = df[df["span"] <= 1.0].copy()
    df["time_s"] = df["iend"]
    df["throughput_mbps"] = df["speed"] / 1e6
    df["rtt_ms"] = df["tcprtt"] / 1000.0
    return df


def plot_throughput_by_bw(df_single: pd.DataFrame, bw: int, filename: str):
    sub = df_single[df_single["bandwidth_mbps"] == bw]
    delays = [0, 10, 100]
    losses = [0, 1, 5]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    x = np.arange(len(losses))
    width = 0.35

    for idx, d in enumerate(delays):
        ax = axes[idx]
        s_d = sub[sub["delay_ms"] == d]
        c_vals = [
            s_d[(s_d["algorithm"] == "cubic") & (s_d["loss_pct"] == l)]["throughput_total_mbps"].values[0]
            for l in losses
        ]
        v_vals = [
            s_d[(s_d["algorithm"] == "vegas") & (s_d["loss_pct"] == l)]["throughput_total_mbps"].values[0]
            for l in losses
        ]

        bars1 = ax.bar(x - width / 2, c_vals, width, label=LABELS["cubic"], color=COLORS["cubic"], edgecolor="black", linewidth=0.6)
        bars2 = ax.bar(x + width / 2, v_vals, width, label=LABELS["vegas"], color=COLORS["vegas"], edgecolor="black", linewidth=0.6)

        ax.set_title(f"Delay = {d} ms", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{l}%" for l in losses])
        ax.set_xlabel("Perda Configurada (Loss)")
        if idx == 0:
            ax.set_ylabel("Throughput Médio (Mbps)")

        for bars in (bars1, bars2):
            for b in bars:
                h = b.get_height()
                ax.annotate(
                    f"{h:.1f}",
                    xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    bw_label = "100 Mbps" if bw == 100 else "1 Gbps"
    ymax = sub["throughput_total_mbps"].max()
    axes[0].set_ylim(0, ymax * 1.14)
    fig.suptitle(f"Comparação de Throughput Médio: TCP CUBIC vs TCP Vegas (Banda: {bw_label})", fontsize=14, fontweight="bold")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.96), frameon=True)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(IMG_DIR / filename, dpi=200)
    plt.close(fig)


def plot_latency_comparison(df_single: pd.DataFrame):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
    bws = [100, 1000]
    delays = [0, 10, 100]
    losses = [0, 1, 5]
    x = np.arange(len(losses))
    width = 0.35

    for r_idx, bw in enumerate(bws):
        bw_label = "100 Mbps" if bw == 100 else "1 Gbps"
        for c_idx, d in enumerate(delays):
            ax = axes[r_idx, c_idx]
            sub = df_single[(df_single["bandwidth_mbps"] == bw) & (df_single["delay_ms"] == d)]
            c_vals = [
                sub[(sub["algorithm"] == "cubic") & (sub["loss_pct"] == l)]["rtt_mean_ms"].values[0]
                for l in losses
            ]
            v_vals = [
                sub[(sub["algorithm"] == "vegas") & (sub["loss_pct"] == l)]["rtt_mean_ms"].values[0]
                for l in losses
            ]

            b1 = ax.bar(x - width / 2, c_vals, width, label=LABELS["cubic"], color=COLORS["cubic"], edgecolor="black", linewidth=0.6)
            b2 = ax.bar(x + width / 2, v_vals, width, label=LABELS["vegas"], color=COLORS["vegas"], edgecolor="black", linewidth=0.6)

            ax.set_title(f"{bw_label} | Delay = {d} ms", fontsize=11, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels([f"{l}%" for l in losses])
            if r_idx == 1:
                ax.set_xlabel("Perda Configurada (Loss)")
            if c_idx == 0:
                ax.set_ylabel("RTT Médio (ms)")

            ax.set_ylim(0, max(c_vals + v_vals) * 1.15)
            for bars in (b1, b2):
                for b in bars:
                    h = b.get_height()
                    ax.annotate(
                        f"{h:.1f}",
                        xy=(b.get_x() + b.get_width() / 2, h),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7.5,
                    )

    fig.suptitle("Comparação de Latência Média (RTT): TCP CUBIC vs TCP Vegas", fontsize=14, fontweight="bold")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.97), frameon=True)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(IMG_DIR / "latencia_rtt.png", dpi=200)
    plt.close(fig)


def plot_loss_and_retries(df_single: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))

    # Painel esquerdo: Retransmissões TCP totais (média por perda configurada)
    losses = [0, 1, 5]
    x = np.arange(len(losses))
    width = 0.35

    for idx, bw in enumerate([100, 1000]):
        ax = axes[idx]
        sub = df_single[df_single["bandwidth_mbps"] == bw]
        c_vals = [sub[(sub["algorithm"] == "cubic") & (sub["loss_pct"] == l)]["tc_loss_rate_pct"].mean() for l in losses]
        v_vals = [sub[(sub["algorithm"] == "vegas") & (sub["loss_pct"] == l)]["tc_loss_rate_pct"].mean() for l in losses]

        b1 = ax.bar(x - width / 2, c_vals, width, label=LABELS["cubic"], color=COLORS["cubic"], edgecolor="black", linewidth=0.6)
        b2 = ax.bar(x + width / 2, v_vals, width, label=LABELS["vegas"], color=COLORS["vegas"], edgecolor="black", linewidth=0.6)

        bw_label = "100 Mbps" if bw == 100 else "1 Gbps"
        ax.set_title(f"Taxa de Perda Efetiva na Fila (Banda: {bw_label})", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Loss {l}%" for l in losses])
        ax.set_ylabel("Taxa Média de Perda de Pacotes (%)")
        ax.legend()

        for bars in (b1, b2):
            for b in bars:
                h = b.get_height()
                ax.annotate(
                    f"{h:.2f}%",
                    xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8.5,
                )

    fig.suptitle("Taxa Média de Perda de Pacotes Observada (tc netem): CUBIC vs Vegas", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(IMG_DIR / "taxa_perda_pacotes.png", dpi=200)
    plt.close(fig)

    # Segundo gráfico: Retransmissões TCP por cenário (delay x loss em 100 Mbps e 1 Gbps)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    for idx, bw in enumerate([100, 1000]):
        ax = axes[idx]
        sub = df_single[df_single["bandwidth_mbps"] == bw]
        c_vals = [sub[(sub["algorithm"] == "cubic") & (sub["loss_pct"] == l)]["tcp_retries"].mean() for l in losses]
        v_vals = [sub[(sub["algorithm"] == "vegas") & (sub["loss_pct"] == l)]["tcp_retries"].mean() for l in losses]

        b1 = ax.bar(x - width / 2, c_vals, width, label=LABELS["cubic"], color=COLORS["cubic"], edgecolor="black", linewidth=0.6)
        b2 = ax.bar(x + width / 2, v_vals, width, label=LABELS["vegas"], color=COLORS["vegas"], edgecolor="black", linewidth=0.6)

        bw_label = "100 Mbps" if bw == 100 else "1 Gbps"
        ax.set_title(f"Média de Retransmissões TCP (Banda: {bw_label})", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Loss {l}%" for l in losses])
        ax.set_ylabel("Retransmissões TCP (média em 30s)")
        ax.legend()

        for bars in (b1, b2):
            for b in bars:
                h = b.get_height()
                ax.annotate(
                    f"{h:.0f}",
                    xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8.5,
                )

    fig.suptitle("Retransmissões TCP (iPerf -e): CUBIC vs Vegas", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(IMG_DIR / "retransmissoes_tcp.png", dpi=200)
    plt.close(fig)


def plot_concurrent_scenario():
    c_path = RAW_DIR / "concurrent_cubic_bw100M_d0ms_l0pct.csv"
    v_path = RAW_DIR / "concurrent_vegas_bw100M_d0ms_l0pct.csv"
    if not (c_path.exists() and v_path.exists()):
        return

    df_c = load_raw_series(c_path)
    df_v = load_raw_series(v_path)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True)

    # Throughput ao longo do tempo (série de 0,1s + média móvel de 1s para clareza visual)
    ax1.plot(df_c["time_s"], df_c["throughput_mbps"], color=COLORS["cubic"], alpha=0.25, linewidth=0.9)
    ax1.plot(df_v["time_s"], df_v["throughput_mbps"], color=COLORS["vegas"], alpha=0.25, linewidth=0.9)
    ax1.plot(df_c["time_s"], df_c["throughput_mbps"].rolling(10, min_periods=1).mean(), label=f"{LABELS['cubic']} — Média móvel 1s (Total: 95,23 Mbps)", color=COLORS["cubic"], linewidth=2.2)
    ax1.plot(df_v["time_s"], df_v["throughput_mbps"].rolling(10, min_periods=1).mean(), label=f"{LABELS['vegas']} — Média móvel 1s (Total: 5,53 Mbps)", color=COLORS["vegas"], linewidth=2.2)
    ax1.set_ylabel("Throughput (Mbps)")
    ax1.set_title("Cenário Concorrente (CUBIC x Vegas) em 100 Mbps, 0 ms, 0% Loss — Throughput ao Longo do Tempo", fontsize=12, fontweight="bold")
    ax1.legend(loc="upper right", frameon=True)

    ax2.plot(df_c["time_s"], df_c["rtt_ms"], label=f"{LABELS['cubic']} (RTT médio: {df_c['rtt_ms'].mean():.2f} ms)", color=COLORS["cubic"], alpha=0.9, linewidth=1.6)
    ax2.plot(df_v["time_s"], df_v["rtt_ms"], label=f"{LABELS['vegas']} (RTT médio: {df_v['rtt_ms'].mean():.2f} ms)", color=COLORS["vegas"], alpha=0.9, linewidth=1.6)
    ax2.set_xlabel("Tempo (s)")
    ax2.set_ylabel("RTT (ms)")
    ax2.set_title("Evolução do RTT (Latência) Durante a Competição CUBIC x Vegas", fontsize=12, fontweight="bold")
    ax2.legend(loc="lower right", frameon=True)

    fig.tight_layout()
    fig.savefig(IMG_DIR / "concorrencia_cubic_vs_vegas.png", dpi=200)
    plt.close(fig)


def plot_representative_timeseries():
    """Plota séries temporais de 4 cenários representativos para ilustrar dinâmica temporal."""
    cases = [
        (100, 10, 0, "100 Mbps | Delay 10 ms | Loss 0%"),
        (100, 10, 1, "100 Mbps | Delay 10 ms | Loss 1%"),
        (100, 100, 1, "100 Mbps | Delay 100 ms | Loss 1%"),
        (1000, 10, 1, "1 Gbps | Delay 10 ms | Loss 1%"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 8.2))
    for ax, (bw, d, l, title) in zip(axes.flat, cases):
        c_file = RAW_DIR / f"single_cubic_bw{bw}M_d{d}ms_l{l}pct.csv"
        v_file = RAW_DIR / f"single_vegas_bw{bw}M_d{d}ms_l{l}pct.csv"
        if not (c_file.exists() and v_file.exists()):
            continue
        df_c = load_raw_series(c_file)
        df_v = load_raw_series(v_file)
        ax.plot(df_c["time_s"], df_c["throughput_mbps"], label=LABELS["cubic"], color=COLORS["cubic"], alpha=0.8, linewidth=1.2)
        ax.plot(df_v["time_s"], df_v["throughput_mbps"], label=LABELS["vegas"], color=COLORS["vegas"], alpha=0.8, linewidth=1.2)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Throughput (Mbps)")
        ax.legend(loc="upper right")

    fig.suptitle("Evolução Temporal do Throughput (Intervalos de 0,1s): Cenários Representativos", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "series_temporais_cenarios.png", dpi=200)
    plt.close(fig)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SUMMARY_CSV)
    df_single = df[df["scenario"] == "single"].copy()

    plot_throughput_by_bw(df_single, 100, "throughput_100mbps.png")
    plot_throughput_by_bw(df_single, 1000, "throughput_1gbps.png")
    plot_latency_comparison(df_single)
    plot_loss_and_retries(df_single)
    plot_concurrent_scenario()
    plot_representative_timeseries()

    print(f"[SUCESSO] Gráficos gerados em: {IMG_DIR}")


if __name__ == "__main__":
    main()
