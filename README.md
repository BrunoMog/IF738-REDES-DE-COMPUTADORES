# IF738 - Redes de Computadores

Repositório destinado ao armazenamento das atividades práticas e da apresentação de protocolo da disciplina **IF738 - Redes de Computadores** (CIn - UFPE).

## Sobre a Disciplina

IF738 aborda os fundamentos práticos e teóricos de redes de computadores, incluindo roteamento estático, controle de congestionamento TCP, simulação de redes com NS-3 e protocolos de segurança na camada de rede.

---

## Estrutura do Repositório

### 1. [Atividade 1 — Topologia de Rede com Mininet](atividade_1/)
Criação e configuração de uma topologia de rede no Mininet com **4 hosts** (`h1`–`h4`), **3 roteadores** (`r1`–`r3`) e **4 sub-redes (LANs)**, garantindo conectividade fim-a-fim por meio de roteamento estático.
- **Arquivos principais:** [`main.py`](atividade_1/main.py), [`minha_topologia.py`](atividade_1/minha_topologia.py), [`relatorio.md`](atividade_1/relatorio.md)
- **Tecnologias:** Mininet, Python, Linux Networking (`ip route`, `sysctl`)

---

### 2. [Atividade 2 — Avaliação de Protocolos de Controle de Congestionamento (TCP CUBIC vs TCP Vegas)](atividade_2/)
Estudo experimental comparativo entre **TCP CUBIC** (*loss-based*) e **TCP Vegas** (*delay-based*) em **37 cenários** variando largura de banda (`100 Mbps`, `1 Gbps`), atraso (`0 ms`, `10 ms`, `100 ms`), perda (`0%`, `1%`, `5%`) e concorrência direta (`CUBIC × Vegas`), medindo throughput médio/mediano, RTT, perda efetiva e retransmissões TCP.
- **Arquivos principais:** [`run_experiments.py`](atividade_2/run_experiments.py), [`gerar_graficos.py`](atividade_2/gerar_graficos.py), [`dados/resumo_experimentos.csv`](atividade_2/dados/resumo_experimentos.csv), [`relatorio.md`](atividade_2/relatorio.md)
- **Tecnologias:** iPerf 2, `tc/netem`, `sysctl`, Python (`matplotlib`, `pandas`, `numpy`)

---

### 3. [Atividade 3 — Simulação de Protocolos de Transporte no NS-3 (Topologia Dumbbell)](atividade_3/)
Simulação em C++ no **NS-3 (v3.41)** com topologia *Dumbbell* e gargalo `DropTail` (`100 Mbps`, `10 ms`), avaliando a competição simultânea entre **Fluxo 1 (UDP 3 Mbps)**, **Fluxo 2 (TCP Bulk)** e **Fluxo 3 (aplicação TCP customizada `CustomTcpApp` herdando de `ns3::Application`)** enviando blocos de 50.000 Bytes com pausas exatas de 2,0 s agendadas via `Simulator::Schedule`.
- **Arquivos principais:** [`src/simulacao_dumbbell.cc`](atividade_3/src/simulacao_dumbbell.cc), [`src/custom-tcp-app.h`](atividade_3/src/custom-tcp-app.h), [`src/custom-tcp-app.cc`](atividade_3/src/custom-tcp-app.cc), [`Dockerfile`](atividade_3/Dockerfile), [`build_and_run.sh`](atividade_3/build_and_run.sh), [`gerar_graficos.py`](atividade_3/gerar_graficos.py), [`relatorio.md`](atividade_3/relatorio.md), [`entrega_ns3.zip`](atividade_3/entrega_ns3.zip)
- **Tecnologias:** NS-3 (C++20), Docker, Python (`matplotlib`, `pandas`)

---

### 4. [Apresentação Prática — VPN Site-to-Site com IPsec (IKEv2 / ESP)](apresentacao_protocolo/)
Configuração e demonstração prática de um túnel VPN **IPsec (IKEv2 + ESP em modo túnel)** entre duas máquinas virtuais Debian 12 (`Site-A` e `Site-B`) usando **strongSwan** e análise ao vivo no **Wireshark**. *(As imagens `.ova` das VMs não são versionadas no Git devido ao tamanho; em seu lugar, o repositório inclui os arquivos de configuração, a captura completa `.pcapng`, os slides e o relatório técnico).*
- **Arquivos principais:** [`relatorio.md`](apresentacao_protocolo/relatorio.md), [`capturas/ipsec_demo.pcapng`](apresentacao_protocolo/capturas/ipsec_demo.pcapng), [`configs/`](apresentacao_protocolo/configs/), [`IPsec (IKEv2 ESP).pdf`](apresentacao_protocolo/IPsec%20(IKEv2%20ESP).pdf), [`roteiro_apresentacao_ipsec.md`](apresentacao_protocolo/roteiro_apresentacao_ipsec.md)
- **Tecnologias:** strongSwan (IPsec IKEv2/ESP), Linux XFRM, VirtualBox, Wireshark / tshark

---

## Autor

**Bruno Antonio dos Santos Bezerra** (`basb`)
