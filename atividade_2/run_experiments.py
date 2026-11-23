#!/usr/bin/env python3
"""
Script automatizado para a Atividade 2 - Avaliação de Desempenho entre Protocolos de Congestão.
Executa os 37 experimentos (TCP CUBIC vs TCP Vegas) usando iPerf 2 e tc netem na interface lo.

Uso:
    sudo python3 run_experiments.py
"""

import csv
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dados"
RAW_DIR = DATA_DIR / "raw"
SUMMARY_CSV = DATA_DIR / "resumo_experimentos.csv"

DURATION = 30          # segundos por experimento (-t 30)
INTERVAL = 0.1         # intervalo de medição (-i 0.1)
PORT_MAIN = 5001
PORT_SECOND = 5002

DELAYS_MS = [0, 10, 100]
LOSSES_PCT = [0, 1, 5]
BANDWIDTHS_MBPS = [100, 1000]  # 100 Mbps e 1 Gbps
ALGORITHMS = ["cubic", "vegas"]

server_procs = []
original_cc = "cubic"


def run_cmd(cmd, check=True, capture=True):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def clear_tc():
    subprocess.run(
        ["tc", "qdisc", "del", "dev", "lo", "root"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def apply_tc(bw_mbps: int, delay_ms: int, loss_pct: int):
    clear_tc()
    cmd = ["tc", "qdisc", "add", "dev", "lo", "root", "netem", "rate", f"{bw_mbps}mbit"]
    if delay_ms > 0:
        cmd += ["delay", f"{delay_ms}ms"]
    if loss_pct > 0:
        cmd += ["loss", f"{loss_pct}%"]
    # Limite suficiente para suportar alto BDP (ex.: 1 Gbps @ 100 ms) sem gargalo artificial de fila minúscula
    cmd += ["limit", "10000"]
    run_cmd(cmd)


def get_tc_stats():
    """Retorna (sent_bytes, sent_pkts, dropped_pkts) do qdisc root de lo."""
    res = run_cmd(["tc", "-s", "qdisc", "show", "dev", "lo"])
    m = re.search(r"Sent\s+(\d+)\s+bytes\s+(\d+)\s+pkt\s+\(dropped\s+(\d+),", res.stdout)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 0, 0, 0


def set_congestion_control(algo: str):
    run_cmd(["sysctl", "-w", f"net.ipv4.tcp_congestion_control={algo}"])


def parse_iperf_csv(csv_path: Path):
    """
    Faz o parsing do CSV gerado por `iperf -c ... -i 0.1 -e -y C`.
    Formato das colunas:
    time,srcaddress,srcport,dstaddr,dstport,transferid,istart,iend,bytes,speed,writecnt,writeerr,tcpretry,tcpcwnd,tcppcwnd,tcprtt,tcprttvar
    """
    intervals = []
    summary_row = None

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return None

    # A última linha geralmente é o resumo total (istart=0.0 e iend >= duration - 1)
    for idx, r in enumerate(rows):
        try:
            istart = float(r["istart"])
            iend = float(r["iend"])
            span = iend - istart
            entry = {
                "istart": istart,
                "iend": iend,
                "bytes": int(r["bytes"]),
                "speed_mbps": float(r["speed"]) / 1e6,
                "writecnt": int(r["writecnt"]),
                "writeerr": int(r["writeerr"]),
                "tcpretry": int(r["tcpretry"]),
                "tcpcwnd_kb": float(r["tcpcwnd"]),
                "tcppcwnd": float(r["tcppcwnd"]),
                "tcprtt_ms": float(r["tcprtt"]) / 1000.0,
                "tcprttvar_ms": float(r["tcprttvar"]) / 1000.0,
            }
            if idx == len(rows) - 1 and span > 1.0:
                summary_row = entry
            else:
                intervals.append(entry)
        except (ValueError, KeyError):
            continue

    if not intervals and summary_row:
        intervals = [summary_row]

    speeds = sorted(x["speed_mbps"] for x in intervals)
    rtts = [x["tcprtt_ms"] for x in intervals if x["tcprtt_ms"] > 0]
    cwnds = [x["tcpcwnd_kb"] for x in intervals if x["tcpcwnd_kb"] > 0]

    n = len(speeds)
    median_speed = speeds[n // 2] if n % 2 == 1 else (speeds[n // 2 - 1] + speeds[n // 2]) / 2.0
    mean_speed = sum(speeds) / n if n else 0.0
    mean_rtt = sum(rtts) / len(rtts) if rtts else 0.0
    mean_cwnd = sum(cwnds) / len(cwnds) if cwnds else 0.0

    total_bytes = summary_row["bytes"] if summary_row else sum(x["bytes"] for x in intervals)
    total_speed = summary_row["speed_mbps"] if summary_row else mean_speed
    total_retries = summary_row["tcpretry"] if summary_row else sum(x["tcpretry"] for x in intervals)
    total_writes = summary_row["writecnt"] if summary_row else sum(x["writecnt"] for x in intervals)

    return {
        "throughput_total_mbps": round(total_speed, 4),
        "throughput_mean_mbps": round(mean_speed, 4),
        "throughput_median_mbps": round(median_speed, 4),
        "rtt_mean_ms": round(mean_rtt, 4),
        "cwnd_mean_kb": round(mean_cwnd, 2),
        "total_bytes": total_bytes,
        "tcp_retries": total_retries,
        "write_cnt": total_writes,
        "num_intervals": n,
    }


def cleanup(signum=None, frame=None):
    print("\n[CLEANUP] Removendo regras tc e encerrando servidores iPerf...")
    clear_tc()
    for p in server_procs:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
    try:
        set_congestion_control(original_cc)
    except Exception:
        pass
    if signum is not None:
        sys.exit(1)


def main():
    global original_cc

    if os.geteuid() != 0:
        print("ERRO: Este script precisa ser executado como root (use sudo python3 run_experiments.py).")
        sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Salva algoritmo original e carrega tcp_vegas
    original_cc = run_cmd(["sysctl", "-n", "net.ipv4.tcp_congestion_control"]).stdout.strip()
    print(f"[INFO] Algoritmo TCP original: {original_cc}")
    print("[INFO] Carregando módulo tcp_vegas via modprobe...")
    run_cmd(["modprobe", "tcp_vegas"])
    avail = run_cmd(["sysctl", "-n", "net.ipv4.tcp_available_congestion_control"]).stdout.strip()
    print(f"[INFO] Algoritmos disponíveis: {avail}")
    if "vegas" not in avail or "cubic" not in avail:
        print("ERRO: cubic e vegas precisam estar disponíveis!")
        sys.exit(1)

    # Permite uso de ambos via -Z sem restrições
    run_cmd(["sysctl", "-w", "net.ipv4.tcp_allowed_congestion_control=reno cubic vegas"])

    # Inicia dois servidores iPerf (5001 para fluxo principal, 5002 para cenário concorrente)
    print(f"[INFO] Iniciando servidores iPerf nas portas {PORT_MAIN} e {PORT_SECOND}...")
    srv1 = subprocess.Popen(
        ["iperf", "-s", "-p", str(PORT_MAIN)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    srv2 = subprocess.Popen(
        ["iperf", "-s", "-p", str(PORT_SECOND)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    server_procs.extend([srv1, srv2])
    time.sleep(0.5)

    results = []
    total_exps = len(BANDWIDTHS_MBPS) * len(DELAYS_MS) * len(LOSSES_PCT) * len(ALGORITHMS) + 1
    exp_idx = 0
    t0_all = time.time()

    try:
        # 1) 36 experimentos individuais (1 cliente)
        for bw in BANDWIDTHS_MBPS:
            for delay in DELAYS_MS:
                for loss in LOSSES_PCT:
                    for algo in ALGORITHMS:
                        exp_idx += 1
                        exp_name = f"single_{algo}_bw{bw}M_d{delay}ms_l{loss}pct"
                        raw_csv = RAW_DIR / f"{exp_name}.csv"

                        print(
                            f"\n[{exp_idx}/{total_exps}] Executando {exp_name} "
                            f"(algo={algo}, bw={bw}Mbps, delay={delay}ms, loss={loss}%, t={DURATION}s)..."
                        )

                        set_congestion_control(algo)
                        apply_tc(bw, delay, loss)
                        time.sleep(0.2)

                        cmd = [
                            "iperf",
                            "-c", "127.0.0.1",
                            "-p", str(PORT_MAIN),
                            "-Z", algo,
                            "-t", str(DURATION),
                            "-i", str(INTERVAL),
                            "-e",
                            "-y", "C",
                        ]
                        res = run_cmd(cmd, check=False)
                        raw_csv.write_text(res.stdout)

                        sent_bytes, sent_pkts, dropped_pkts = get_tc_stats()
                        tc_total_pkts = sent_pkts + dropped_pkts
                        tc_loss_pct = (dropped_pkts / tc_total_pkts * 100.0) if tc_total_pkts > 0 else 0.0

                        metrics = parse_iperf_csv(raw_csv)
                        if metrics is None:
                            print(f"  [AVISO] Falha ao parsear {raw_csv}. stderr: {res.stderr.strip()}")
                            metrics = {
                                "throughput_total_mbps": 0.0,
                                "throughput_mean_mbps": 0.0,
                                "throughput_median_mbps": 0.0,
                                "rtt_mean_ms": 0.0,
                                "cwnd_mean_kb": 0.0,
                                "total_bytes": 0,
                                "tcp_retries": 0,
                                "write_cnt": 0,
                                "num_intervals": 0,
                            }

                        row = {
                            "exp_id": exp_idx,
                            "scenario": "single",
                            "exp_name": exp_name,
                            "algorithm": algo,
                            "bandwidth_mbps": bw,
                            "delay_ms": delay,
                            "loss_pct": loss,
                            "tc_sent_pkts": sent_pkts,
                            "tc_dropped_pkts": dropped_pkts,
                            "tc_loss_rate_pct": round(tc_loss_pct, 4),
                            **metrics,
                        }
                        results.append(row)

                        elapsed = time.time() - t0_all
                        print(
                            f"  -> Throughput={row['throughput_total_mbps']:.2f} Mbps "
                            f"(mediana={row['throughput_median_mbps']:.2f}), "
                            f"RTT={row['rtt_mean_ms']:.2f} ms, "
                            f"TCP Retries={row['tcp_retries']}, "
                            f"TC Drops={dropped_pkts} ({tc_loss_pct:.2f}%) "
                            f"[tempo decorrido: {elapsed/60:.1f} min]"
                        )

        # 2) Experimento 37: CUBIC x Vegas concorrentes (100 Mbps, 0 ms, 0% loss)
        exp_idx += 1
        print(f"\n[{exp_idx}/{total_exps}] Executando cenário concorrente CUBIC x Vegas (100 Mbps, 0 ms, 0% loss)...")
        set_congestion_control("cubic")
        apply_tc(100, 0, 0)
        time.sleep(0.2)

        raw_cubic = RAW_DIR / "concurrent_cubic_bw100M_d0ms_l0pct.csv"
        raw_vegas = RAW_DIR / "concurrent_vegas_bw100M_d0ms_l0pct.csv"

        cmd_cubic = [
            "iperf", "-c", "127.0.0.1", "-p", str(PORT_MAIN),
            "-Z", "cubic", "-t", str(DURATION), "-i", str(INTERVAL), "-e", "-y", "C"
        ]
        cmd_vegas = [
            "iperf", "-c", "127.0.0.1", "-p", str(PORT_SECOND),
            "-Z", "vegas", "-t", str(DURATION), "-i", str(INTERVAL), "-e", "-y", "C"
        ]

        p_cubic = subprocess.Popen(cmd_cubic, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p_vegas = subprocess.Popen(cmd_vegas, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        out_c, err_c = p_cubic.communicate()
        out_v, err_v = p_vegas.communicate()

        raw_cubic.write_text(out_c)
        raw_vegas.write_text(out_v)

        sent_bytes, sent_pkts, dropped_pkts = get_tc_stats()
        tc_total_pkts = sent_pkts + dropped_pkts
        tc_loss_pct = (dropped_pkts / tc_total_pkts * 100.0) if tc_total_pkts > 0 else 0.0

        for algo, raw_file in [("cubic", raw_cubic), ("vegas", raw_vegas)]:
            metrics = parse_iperf_csv(raw_file) or {
                "throughput_total_mbps": 0.0,
                "throughput_mean_mbps": 0.0,
                "throughput_median_mbps": 0.0,
                "rtt_mean_ms": 0.0,
                "cwnd_mean_kb": 0.0,
                "total_bytes": 0,
                "tcp_retries": 0,
                "write_cnt": 0,
                "num_intervals": 0,
            }
            row = {
                "exp_id": exp_idx,
                "scenario": "concurrent_cubic_vs_vegas",
                "exp_name": f"concurrent_{algo}_bw100M_d0ms_l0pct",
                "algorithm": algo,
                "bandwidth_mbps": 100,
                "delay_ms": 0,
                "loss_pct": 0,
                "tc_sent_pkts": sent_pkts,
                "tc_dropped_pkts": dropped_pkts,
                "tc_loss_rate_pct": round(tc_loss_pct, 4),
                **metrics,
            }
            results.append(row)
            print(
                f"  -> [{algo.upper()}] Throughput={row['throughput_total_mbps']:.2f} Mbps "
                f"(mediana={row['throughput_median_mbps']:.2f}), "
                f"RTT={row['rtt_mean_ms']:.2f} ms, TCP Retries={row['tcp_retries']}"
            )

        # Salvar CSV consolidado
        fieldnames = list(results[0].keys())
        with open(SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        # Ajustar permissões para o usuário normal se executado via sudo
        sudo_uid = os.environ.get("SUDO_UID")
        sudo_gid = os.environ.get("SUDO_GID")
        if sudo_uid and sudo_gid:
            uid, gid = int(sudo_uid), int(sudo_gid)
            for root_dir, dirs, files in os.walk(DATA_DIR):
                os.chown(root_dir, uid, gid)
                for fn in files:
                    os.chown(os.path.join(root_dir, fn), uid, gid)

        print(f"\n[SUCESSO] Todos os {total_exps} experimentos concluídos! Resumo salvo em: {SUMMARY_CSV}")

    finally:
        cleanup()


if __name__ == "__main__":
    main()
