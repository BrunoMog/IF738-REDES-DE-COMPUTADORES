# Atividade de Avaliação de Desempenho entre Protocolos de Congestão

## Instruções

### Objetivo

O objetivo desta atividade é realizar uma avaliação comparativa de desempenho entre pelo menos dois protocolos de congestionamento em redes, utilizando o **iperf** ou outras ferramentas para gerar tráfego de rede e, por fim, coletar e analisar métricas relevantes. O objetivo é desafiar vocês a explorar e comparar o impacto de diferentes protocolos de congestionamento, como o **TCP Vegas**, sobre o desempenho da rede.

### Passos da Atividade

#### 1. Geração de Tráfego de Rede com o iPerf

##### 1.1 Verificação do Desempenho com o iPerf

O **iPerf** será utilizado para gerar tráfego TCP entre os hosts da rede. O iPerf permite medir o desempenho de rede entre dois pontos, proporcionando métricas como a largura de banda, latência e taxa de perda de pacotes.

##### 1.2 Iniciar o Servidor iPerf

Em um dos hosts, execute o iPerf em modo servidor (ou seja, estará aguardando conexões):

```bash
iperf -s
```

##### 1.3 Iniciar o Cliente iPerf

No outro host, execute o iPerf em modo cliente, especificando o endereço IP do servidor iPerf (geralmente, o IP do host que está executando o iPerf em modo servidor):

```bash
iperf -c <IP_DO_SERVIDOR> -Z vegas -t 30 -i 0.1 -e
```

Este comando gera um fluxo de tráfego TCP por 30 segundos, com medições de desempenho a cada 0,1 segundo.

#### 2. Mudança de Protocolos de Congestionamento

##### 2.1 Variando Algoritmos de Controle de Congestionamento

O objetivo agora é testar como o desempenho da rede muda ao trocar o protocolo de congestionamento TCP utilizado. No Linux, você pode usar o comando `sysctl` para alterar o protocolo de congestionamento TCP. O protocolo padrão é o **TCP CUBIC**, mas você pode alterar para outros protocolos como **TCP Vegas**.

Veja qual algoritmo está sendo utilizado:

```bash
sysctl net.ipv4.tcp_congestion_control
cat /proc/sys/net/ipv4/tcp_congestion_control
```

Observe os algoritmos disponíveis:

```bash
sudo sysctl net.ipv4.tcp_available_congestion_control
```

Caso algum algoritmo não esteja disponível, ative-o usando o `modprobe`. Exemplo:

```bash
sudo modprobe tcp_vegas
```

Exemplo para alterar o protocolo para Vegas:

```bash
sudo sysctl -w net.ipv4.tcp_congestion_control=vegas
```

Outros protocolos podem ser testados da seguinte maneira:

* **TCP Cubic:**

```bash
sudo sysctl -w net.ipv4.tcp_congestion_control=cubic
```

* **TCP Vegas:**

```bash
sudo sysctl -w net.ipv4.tcp_congestion_control=vegas
```

##### 2.2 Variando as Condições da Rede

No link entre o servidor e o(s) cliente(s), varie os seguintes parâmetros:

1. **Delay:**
   - 0 ms
   - 10 ms
   - 100 ms
2. **Loss:**
   - 0%
   - 1%
   - 5%
3. **Bandwidth:**
   - 100 Mbps
   - 1 Gbps
4. **Cenários do controle de congestionamento:**
   - CUBIC x Vegas (2 clientes — neste cenário não é preciso variar a banda, o delay ou a loss)
   - CUBIC (apenas 1 cliente)
   - Vegas (apenas 1 cliente)

> **Total de experimentos:** 3 × 3 × 2 × 2 + 1 = **37**
>
> Obs.: usar os valores padrão de 100 Mbps, 0 ms e 0% de loss para o cenário CUBIC x Vegas.

Exemplo de variação do delay (100 ms):

```bash
sudo tc qdisc add dev lo root netem delay 100ms
```

Exemplo de variação do loss (1%):

```bash
sudo tc qdisc add dev lo root netem loss 1%
```

Exemplo de variação da banda (100 Mbps):

```bash
sudo tc qdisc add dev lo root netem rate 100mbit
```

Para remover alguma regra aplicada:

```bash
sudo tc qdisc del dev lo root
```

#### 3. Coleta de Métricas e Geração de Gráficos

##### 3.1 Métricas a Serem Coletadas

* Média ou mediana da largura de banda (throughput);
* Média da latência;
* Média da taxa de perda de pacotes.

##### 3.2 Gerar Gráficos

Use os resultados do iPerf para gerar gráficos e comparar o desempenho entre os diferentes protocolos de congestionamento. Os dados de desempenho podem ser coletados a partir dos resultados do iPerf. Para isso, é interessante exportar os dados para um arquivo CSV ou JSON, o que permitirá a criação de gráficos mais detalhados.

Exemplo ilustrativo para gerar gráficos com Python e a biblioteca **Matplotlib**:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Carregar dados de saída do iPerf
data = pd.read_csv("iperf_results.csv")

# Criar gráfico de Throughput
plt.plot(data['time'], data['bandwidth'])
plt.xlabel('Tempo (s)')
plt.ylabel('Largura de banda (Mbps)')
plt.title('Desempenho de Largura de Banda com TCP Vegas')
plt.show()
```

##### 3.3 Análise e Interpretação dos Gráficos

Analise como a mudança no protocolo de congestionamento afeta o desempenho da rede, especialmente em termos de **largura de banda**, **latência** e **taxa de perda de pacotes**. Compare os diferentes protocolos e tire conclusões sobre a eficiência de cada um em diferentes condições de rede.

#### 4. Conclusão

##### Elaboração de Relatório

Após a realização dos testes, escreva um relatório detalhado que inclua:

* Protocolos de congestionamento testados;
* Explicação das métricas coletadas;
* Análise dos gráficos obtidos;
* Comparação entre as métricas obtidas pelos protocolos.

## Importante

* Realize os testes em diferentes condições de rede (variando a latência, a banda e a perda de pacotes) para observar como cada protocolo se comporta em cenários mais realistas.