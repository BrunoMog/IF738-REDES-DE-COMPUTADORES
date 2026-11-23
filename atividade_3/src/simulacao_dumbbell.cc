#include "custom-tcp-app.h"

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SimulacaoDumbbell");

// Variáveis globais para coleta de métricas
static std::ofstream g_cwndBulkFile;
static std::ofstream g_cwndCustomFile;
static std::ofstream g_rttBulkFile;
static std::ofstream g_rttCustomFile;
static std::ofstream g_throughputFile;

static uint64_t g_bottleneckEnqueued = 0;
static uint64_t g_bottleneckDropped = 0;

static uint64_t g_lastRxUdp = 0;
static uint64_t g_lastRxBulk = 0;
static uint64_t g_lastRxCustom = 0;

static double g_bulkRttSum = 0.0;
static uint64_t g_bulkRttCount = 0;
static double g_customRttSum = 0.0;
static uint64_t g_customRttCount = 0;

static uint64_t g_bulkCwndSum = 0;
static uint64_t g_bulkCwndMax = 0;
static uint64_t g_bulkCwndCount = 0;

static uint64_t g_customCwndSum = 0;
static uint64_t g_customCwndMax = 0;
static uint64_t g_customCwndCount = 0;

static void
BottleneckEnqueueCallback(Ptr<const Packet> packet)
{
    g_bottleneckEnqueued++;
}

static void
BottleneckDropCallback(Ptr<const Packet> packet)
{
    g_bottleneckDropped++;
}

static void
CwndBulkTracer(uint32_t oldVal, uint32_t newVal)
{
    g_cwndBulkFile << Simulator::Now().GetSeconds() << "," << newVal << "\n";
    g_bulkCwndSum += newVal;
    if (newVal > g_bulkCwndMax)
    {
        g_bulkCwndMax = newVal;
    }
    g_bulkCwndCount++;
}

static void
CwndCustomTracer(uint32_t oldVal, uint32_t newVal)
{
    g_cwndCustomFile << Simulator::Now().GetSeconds() << "," << newVal << "\n";
    g_customCwndSum += newVal;
    if (newVal > g_customCwndMax)
    {
        g_customCwndMax = newVal;
    }
    g_customCwndCount++;
}

static void
RttBulkTracer(Time oldVal, Time newVal)
{
    double ms = newVal.GetMilliSeconds() + (newVal.GetMicroSeconds() % 1000) / 1000.0;
    g_rttBulkFile << Simulator::Now().GetSeconds() << "," << ms << "\n";
    g_bulkRttSum += ms;
    g_bulkRttCount++;
}

static void
RttCustomTracer(Time oldVal, Time newVal)
{
    double ms = newVal.GetMilliSeconds() + (newVal.GetMicroSeconds() % 1000) / 1000.0;
    g_rttCustomFile << Simulator::Now().GetSeconds() << "," << ms << "\n";
    g_customRttSum += ms;
    g_customRttCount++;
}

static void
ConnectTcpTraces(Ptr<BulkSendApplication> bulkApp, Ptr<CustomTcpApp> customApp)
{
    Ptr<Socket> bulkSocket = bulkApp->GetSocket();
    if (bulkSocket)
    {
        bulkSocket->TraceConnectWithoutContext("CongestionWindow", MakeCallback(&CwndBulkTracer));
        bulkSocket->TraceConnectWithoutContext("RTT", MakeCallback(&RttBulkTracer));
    }
    else
    {
        NS_LOG_WARN("Socket do Fluxo 2 (BulkSend) ainda não estava pronto!");
    }

    Ptr<Socket> customSocket = customApp->GetSocket();
    if (customSocket)
    {
        customSocket->TraceConnectWithoutContext("CongestionWindow",
                                                 MakeCallback(&CwndCustomTracer));
        customSocket->TraceConnectWithoutContext("RTT", MakeCallback(&RttCustomTracer));
    }
    else
    {
        NS_LOG_WARN("Socket do Fluxo 3 (CustomTcpApp) ainda não estava pronto!");
    }
}

static void
SampleThroughput(Ptr<PacketSink> sinkUdp,
                 Ptr<PacketSink> sinkBulk,
                 Ptr<PacketSink> sinkCustom,
                 double intervalSec)
{
    uint64_t rxUdp = sinkUdp->GetTotalRx();
    uint64_t rxBulk = sinkBulk->GetTotalRx();
    uint64_t rxCustom = sinkCustom->GetTotalRx();

    double tpUdp = ((rxUdp - g_lastRxUdp) * 8.0) / (intervalSec * 1e6);
    double tpBulk = ((rxBulk - g_lastRxBulk) * 8.0) / (intervalSec * 1e6);
    double tpCustom = ((rxCustom - g_lastRxCustom) * 8.0) / (intervalSec * 1e6);

    g_lastRxUdp = rxUdp;
    g_lastRxBulk = rxBulk;
    g_lastRxCustom = rxCustom;

    g_throughputFile << Simulator::Now().GetSeconds() << "," << tpUdp << "," << tpBulk << ","
                     << tpCustom << "\n";

    if (Simulator::Now().GetSeconds() < 15.5)
    {
        Simulator::Schedule(Seconds(intervalSec),
                            &SampleThroughput,
                            sinkUdp,
                            sinkBulk,
                            sinkCustom,
                            intervalSec);
    }
}

int
main(int argc, char* argv[])
{
    std::string bottleneckRate = "100Mbps";
    std::string bottleneckDelay = "10ms";
    std::string accessRate = "1Gbps";
    std::string accessDelay = "0ms";
    std::string queueSize = "100p";
    std::string outputDir = "resultados";

    CommandLine cmd(__FILE__);
    cmd.AddValue("bottleneckRate", "Taxa do link gargalo R2<->R1", bottleneckRate);
    cmd.AddValue("bottleneckDelay", "Atraso do link gargalo R2<->R1", bottleneckDelay);
    cmd.AddValue("queueSize", "Tamanho da fila DropTail no gargalo", queueSize);
    cmd.AddValue("outputDir", "Diretorio de saida dos CSVs", outputDir);
    cmd.Parse(argc, argv);

    // Configurar segmento TCP padrão e buffer para suportar alto BDP (100 Mbps, 20 ms RTT)
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1448));
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(4194304));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(4194304));

    // =========================================================================
    // 1. Criação dos Nós (Topologia Dumbbell)
    //    Clientes (Destino): Nós 0, 1, 2
    //    Servidores (Origem): Nós 3, 4, 5
    //    Roteadores: R1 (Nó 6) conectado aos clientes, R2 (Nó 7) conectado aos servidores
    // =========================================================================
    NodeContainer hosts;
    hosts.Create(6); // 0, 1, 2 = clientes | 3, 4, 5 = servidores

    NodeContainer routers;
    routers.Create(2); // routers.Get(0) = R1 | routers.Get(1) = R2

    Ptr<Node> node0 = hosts.Get(0);
    Ptr<Node> node1 = hosts.Get(1);
    Ptr<Node> node2 = hosts.Get(2);
    Ptr<Node> node3 = hosts.Get(3);
    Ptr<Node> node4 = hosts.Get(4);
    Ptr<Node> node5 = hosts.Get(5);
    Ptr<Node> r1 = routers.Get(0);
    Ptr<Node> r2 = routers.Get(1);

    // =========================================================================
    // 2. Configuração dos Links Ponto-a-Ponto
    // =========================================================================
    PointToPointHelper accessLink;
    accessLink.SetDeviceAttribute("DataRate", StringValue(accessRate));
    accessLink.SetChannelAttribute("Delay", StringValue(accessDelay));

    PointToPointHelper bottleneckLink;
    bottleneckLink.SetDeviceAttribute("DataRate", StringValue(bottleneckRate));
    bottleneckLink.SetChannelAttribute("Delay", StringValue(bottleneckDelay));
    bottleneckLink.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", StringValue(queueSize));

    // Links Servidores -> R2
    NetDeviceContainer devN3R2 = accessLink.Install(node3, r2);
    NetDeviceContainer devN4R2 = accessLink.Install(node4, r2);
    NetDeviceContainer devN5R2 = accessLink.Install(node5, r2);

    // Link Gargalo R2 <-> R1 (sentido principal de downlink: R2 -> R1)
    NetDeviceContainer devR2R1 = bottleneckLink.Install(r2, r1);

    // Links R1 -> Clientes
    NetDeviceContainer devR1N0 = accessLink.Install(r1, node0);
    NetDeviceContainer devR1N1 = accessLink.Install(r1, node1);
    NetDeviceContainer devR1N2 = accessLink.Install(r1, node2);

    // =========================================================================
    // 3. Pilha de Internet
    // =========================================================================
    InternetStackHelper internet;
    internet.Install(hosts);
    internet.Install(routers);

    // =========================================================================
    // 4. Endereçamento IP, Remoção do QueueDisc padrão (DropTail puro) e Roteamento
    // =========================================================================
    Ipv4AddressHelper ipv4;

    ipv4.SetBase("10.1.3.0", "255.255.255.0");
    Ipv4InterfaceContainer ifN3R2 = ipv4.Assign(devN3R2);

    ipv4.SetBase("10.1.4.0", "255.255.255.0");
    Ipv4InterfaceContainer ifN4R2 = ipv4.Assign(devN4R2);

    ipv4.SetBase("10.1.5.0", "255.255.255.0");
    Ipv4InterfaceContainer ifN5R2 = ipv4.Assign(devN5R2);

    ipv4.SetBase("10.2.0.0", "255.255.255.0");
    Ipv4InterfaceContainer ifR2R1 = ipv4.Assign(devR2R1);

    ipv4.SetBase("10.3.0.0", "255.255.255.0");
    Ipv4InterfaceContainer ifR1N0 = ipv4.Assign(devR1N0);

    ipv4.SetBase("10.3.1.0", "255.255.255.0");
    Ipv4InterfaceContainer ifR1N1 = ipv4.Assign(devR1N1);

    ipv4.SetBase("10.3.2.0", "255.255.255.0");
    Ipv4InterfaceContainer ifR1N2 = ipv4.Assign(devR1N2);

    // Remove o TrafficControlLayer padrão (FqCoDel) instalado pelo Ipv4AddressHelper::Assign
    // para que a fila efetiva do gargalo seja estritamente a DropTailQueue do PointToPointNetDevice.
    TrafficControlHelper tch;
    tch.Uninstall(devR2R1);

    // Conecta os traces de Enqueue e Drop diretamente na fila DropTail de R2 -> R1
    Ptr<PointToPointNetDevice> r2BottleneckDev =
        DynamicCast<PointToPointNetDevice>(devR2R1.Get(0));
    NS_ABORT_MSG_IF(!r2BottleneckDev, "Falha ao obter PointToPointNetDevice de R2");
    Ptr<Queue<Packet>> bottleneckQueue = r2BottleneckDev->GetQueue();
    NS_ABORT_MSG_IF(!bottleneckQueue, "Falha ao obter DropTailQueue de R2");
    bottleneckQueue->TraceConnectWithoutContext("Enqueue",
                                                MakeCallback(&BottleneckEnqueueCallback));
    bottleneckQueue->TraceConnectWithoutContext("DropBeforeEnqueue",
                                                MakeCallback(&BottleneckDropCallback));

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // =========================================================================
    // 5. Aplicações (Início em 1.0s, Fim em 15.0s)
    // =========================================================================
    const double startTime = 1.0;
    const double stopTime = 15.0;
    const double simEnd = 16.0;

    // --- Fluxo 1: Nó 3 -> Nó 0 (UDP 3 Mbps constante via OnOffApplication) ---
    uint16_t portUdp = 5000;
    PacketSinkHelper udpSinkHelper("ns3::UdpSocketFactory",
                                   InetSocketAddress(Ipv4Address::GetAny(), portUdp));
    ApplicationContainer udpSinkApp = udpSinkHelper.Install(node0);
    udpSinkApp.Start(Seconds(0.5));
    udpSinkApp.Stop(Seconds(simEnd));

    OnOffHelper udpClient("ns3::UdpSocketFactory",
                          InetSocketAddress(ifR1N0.GetAddress(1), portUdp));
    udpClient.SetAttribute("DataRate", StringValue("3Mbps"));
    udpClient.SetAttribute("PacketSize", UintegerValue(1024));
    udpClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    udpClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
    ApplicationContainer udpSrcApp = udpClient.Install(node3);
    udpSrcApp.Start(Seconds(startTime));
    udpSrcApp.Stop(Seconds(stopTime));

    // --- Fluxo 2: Nó 4 -> Nó 1 (TCP BulkSendApplication) ---
    uint16_t portBulk = 5001;
    PacketSinkHelper bulkSinkHelper("ns3::TcpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), portBulk));
    ApplicationContainer bulkSinkApp = bulkSinkHelper.Install(node1);
    bulkSinkApp.Start(Seconds(0.5));
    bulkSinkApp.Stop(Seconds(simEnd));

    BulkSendHelper bulkHelper("ns3::TcpSocketFactory",
                              InetSocketAddress(ifR1N1.GetAddress(1), portBulk));
    bulkHelper.SetAttribute("MaxBytes", UintegerValue(0));
    ApplicationContainer bulkSrcApps = bulkHelper.Install(node4);
    bulkSrcApps.Start(Seconds(startTime));
    bulkSrcApps.Stop(Seconds(stopTime));

    // --- Fluxo 3: Nó 5 -> Nó 2 (TCP Customizado - 50.000 Bytes + Pausa 2.0s) ---
    uint16_t portCustom = 5002;
    PacketSinkHelper customSinkHelper("ns3::TcpSocketFactory",
                                      InetSocketAddress(Ipv4Address::GetAny(), portCustom));
    ApplicationContainer customSinkApp = customSinkHelper.Install(node2);
    customSinkApp.Start(Seconds(0.5));
    customSinkApp.Stop(Seconds(simEnd));

    Ptr<CustomTcpApp> customApp = CreateObject<CustomTcpApp>();
    customApp->Setup(InetSocketAddress(ifR1N2.GetAddress(1), portCustom), 50000, Seconds(2.0));
    node5->AddApplication(customApp);
    customApp->SetStartTime(Seconds(startTime));
    customApp->SetStopTime(Seconds(stopTime));

    // =========================================================================
    // 6. Abertura de Arquivos de Trace e Agendamento de Coleta
    // =========================================================================
    g_cwndBulkFile.open(outputDir + "/cwnd_bulk.csv");
    g_cwndBulkFile << "time_s,cwnd_bytes\n";

    g_cwndCustomFile.open(outputDir + "/cwnd_custom.csv");
    g_cwndCustomFile << "time_s,cwnd_bytes\n";

    g_rttBulkFile.open(outputDir + "/rtt_bulk.csv");
    g_rttBulkFile << "time_s,rtt_ms\n";

    g_rttCustomFile.open(outputDir + "/rtt_custom.csv");
    g_rttCustomFile << "time_s,rtt_ms\n";

    g_throughputFile.open(outputDir + "/throughput_series.csv");
    g_throughputFile << "time_s,udp_mbps,bulk_mbps,custom_mbps\n";

    Ptr<BulkSendApplication> bulkAppPtr = DynamicCast<BulkSendApplication>(bulkSrcApps.Get(0));
    // Conecta os traces logo após o início das aplicações (antes do primeiro SYN-ACK)
    Simulator::Schedule(Seconds(startTime + 0.0001), &ConnectTcpTraces, bulkAppPtr, customApp);

    Ptr<PacketSink> sinkUdpPtr = DynamicCast<PacketSink>(udpSinkApp.Get(0));
    Ptr<PacketSink> sinkBulkPtr = DynamicCast<PacketSink>(bulkSinkApp.Get(0));
    Ptr<PacketSink> sinkCustomPtr = DynamicCast<PacketSink>(customSinkApp.Get(0));

    Simulator::Schedule(Seconds(1.2),
                        &SampleThroughput,
                        sinkUdpPtr,
                        sinkBulkPtr,
                        sinkCustomPtr,
                        0.2);

    // FlowMonitor para métricas fim-a-fim de todos os fluxos
    FlowMonitorHelper flowmonHelper;
    Ptr<FlowMonitor> monitor = flowmonHelper.InstallAll();

    // =========================================================================
    // 7. Execução da Simulação
    // =========================================================================
    Simulator::Stop(Seconds(simEnd));
    Simulator::Run();

    // =========================================================================
    // 8. Coleta e Exibição do Resumo de Métricas
    // =========================================================================
    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    const double activeDuration = stopTime - startTime; // 14.0 s
    double tpUdpTotal = (sinkUdpPtr->GetTotalRx() * 8.0) / (activeDuration * 1e6);
    double tpBulkTotal = (sinkBulkPtr->GetTotalRx() * 8.0) / (activeDuration * 1e6);
    double tpCustomTotal = (sinkCustomPtr->GetTotalRx() * 8.0) / (activeDuration * 1e6);

    double dropRatePct =
        (g_bottleneckEnqueued + g_bottleneckDropped > 0)
            ? (static_cast<double>(g_bottleneckDropped) /
               static_cast<double>(g_bottleneckEnqueued + g_bottleneckDropped)) *
                  100.0
            : 0.0;

    double avgBulkRtt = (g_bulkRttCount > 0) ? (g_bulkRttSum / g_bulkRttCount) : 0.0;
    double avgCustomRtt = (g_customRttCount > 0) ? (g_customRttSum / g_customRttCount) : 0.0;
    double avgBulkCwnd = (g_bulkCwndCount > 0) ? (static_cast<double>(g_bulkCwndSum) / g_bulkCwndCount) : 0.0;
    double avgCustomCwnd =
        (g_customCwndCount > 0) ? (static_cast<double>(g_customCwndSum) / g_customCwndCount) : 0.0;

    std::ofstream summaryFile(outputDir + "/resumo.txt");

    auto printBoth = [&](const std::string& line) {
        std::cout << line << "\n";
        summaryFile << line << "\n";
    };

    std::ostringstream oss;
    oss << std::fixed << std::setprecision(4);
    oss << "============================================================\n";
    oss << "RESUMO DA SIMULACAO NS-3 (TOPOLOGIA DUMBBELL)\n";
    oss << "Gargalo: " << bottleneckRate << " | Delay: " << bottleneckDelay
        << " | Fila: DropTail (" << queueSize << ")\n";
    oss << "============================================================\n";
    oss << "VAZAO MEDIA (1.0s - 15.0s, janela = 14.0s):\n";
    oss << "  Fluxo 1 (UDP 3Mbps, No 3 -> No 0):   " << tpUdpTotal << " Mbps ("
        << sinkUdpPtr->GetTotalRx() << " bytes recebidos)\n";
    oss << "  Fluxo 2 (TCP Bulk,  No 4 -> No 1):   " << tpBulkTotal << " Mbps ("
        << sinkBulkPtr->GetTotalRx() << " bytes recebidos)\n";
    oss << "  Fluxo 3 (TCP Custom,No 5 -> No 2):   " << tpCustomTotal << " Mbps ("
        << sinkCustomPtr->GetTotalRx() << " bytes recebidos | " << customApp->GetBlocksSent()
        << " blocos de 50KB enviados)\n\n";

    oss << "RTT MEDIO (Trace TcpSocketBase):\n";
    oss << "  Fluxo 2 (TCP Bulk):                  " << avgBulkRtt << " ms (" << g_bulkRttCount
        << " amostras)\n";
    oss << "  Fluxo 3 (TCP Custom):                " << avgCustomRtt << " ms (" << g_customRttCount
        << " amostras)\n\n";

    oss << "JANELA DE CONGESTIONAMENTO (cwnd):\n";
    oss << "  Fluxo 2 (TCP Bulk):                  Media = " << (avgBulkCwnd / 1024.0)
        << " KB | Max = " << (g_bulkCwndMax / 1024.0) << " KB\n";
    oss << "  Fluxo 3 (TCP Custom):                Media = " << (avgCustomCwnd / 1024.0)
        << " KB | Max = " << (g_customCwndMax / 1024.0) << " KB\n\n";

    oss << "GARGALO (Fila DropTail em R2 -> R1):\n";
    oss << "  Pacotes enfileirados:                " << g_bottleneckEnqueued << "\n";
    oss << "  Pacotes descartados (Drops):         " << g_bottleneckDropped << "\n";
    oss << "  Taxa de Descarte (Drop Rate):        " << dropRatePct << " %\n\n";

    oss << "DETALHES FLOWMONITOR (POR FLUXO IP):\n";
    for (const auto& flow : stats)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(flow.first);
        double avgDelayMs = (flow.second.rxPackets > 0)
                                ? (flow.second.delaySum.GetSeconds() / flow.second.rxPackets) * 1000.0
                                : 0.0;
        double flowTpMbps = (flow.second.rxBytes * 8.0) / (activeDuration * 1e6);
        std::string proto = (t.protocol == 17) ? "UDP" : "TCP";
        oss << "  Flow " << flow.first << " (" << proto << " " << t.sourceAddress << ":"
            << t.sourcePort << " -> " << t.destinationAddress << ":" << t.destinationPort
            << ") | TxPkts=" << flow.second.txPackets << " RxPkts=" << flow.second.rxPackets
            << " Lost=" << flow.second.lostPackets << " | AvgOneWayDelay=" << avgDelayMs
            << " ms | FlowMonTp=" << flowTpMbps << " Mbps\n";
    }
    oss << "============================================================";

    printBoth(oss.str());

    g_cwndBulkFile.close();
    g_cwndCustomFile.close();
    g_rttBulkFile.close();
    g_rttCustomFile.close();
    g_throughputFile.close();
    summaryFile.close();

    Simulator::Destroy();
    return 0;
}
