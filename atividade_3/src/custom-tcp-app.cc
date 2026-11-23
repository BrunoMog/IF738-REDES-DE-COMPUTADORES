#include "custom-tcp-app.h"

#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/tcp-socket-factory.h"
#include "ns3/uinteger.h"

#include <algorithm>

namespace ns3
{

NS_LOG_COMPONENT_DEFINE("CustomTcpApp");
NS_OBJECT_ENSURE_REGISTERED(CustomTcpApp);

TypeId
CustomTcpApp::GetTypeId()
{
    static TypeId tid = TypeId("ns3::CustomTcpApp")
                            .SetParent<Application>()
                            .SetGroupName("Applications")
                            .AddConstructor<CustomTcpApp>();
    return tid;
}

CustomTcpApp::CustomTcpApp()
    : m_socket(nullptr),
      m_blockSize(50000),
      m_pauseDuration(Seconds(2.0)),
      m_bytesRemainingInBlock(0),
      m_totalBytesSent(0),
      m_blocksSent(0),
      m_running(false),
      m_connected(false)
{
}

CustomTcpApp::~CustomTcpApp()
{
    m_socket = nullptr;
}

void
CustomTcpApp::DoDispose()
{
    m_socket = nullptr;
    Application::DoDispose();
}

void
CustomTcpApp::Setup(Address peerAddress, uint32_t blockSize, Time pauseDuration)
{
    m_peer = peerAddress;
    m_blockSize = blockSize;
    m_pauseDuration = pauseDuration;
}

Ptr<Socket>
CustomTcpApp::GetSocket() const
{
    return m_socket;
}

uint64_t
CustomTcpApp::GetTotalBytesSent() const
{
    return m_totalBytesSent;
}

uint32_t
CustomTcpApp::GetBlocksSent() const
{
    return m_blocksSent;
}

void
CustomTcpApp::StartApplication()
{
    m_running = true;
    m_connected = false;
    m_bytesRemainingInBlock = 0;

    if (!m_socket)
    {
        m_socket = Socket::CreateSocket(GetNode(), TcpSocketFactory::GetTypeId());
        m_socket->Bind();
        m_socket->SetConnectCallback(MakeCallback(&CustomTcpApp::ConnectionSucceeded, this),
                                     MakeCallback(&CustomTcpApp::ConnectionFailed, this));
        m_socket->SetSendCallback(MakeCallback(&CustomTcpApp::HandleSend, this));
        m_socket->Connect(m_peer);
    }
}

void
CustomTcpApp::StopApplication()
{
    m_running = false;

    if (m_sendEvent.IsRunning())
    {
        Simulator::Cancel(m_sendEvent);
    }

    if (m_socket)
    {
        m_socket->Close();
        m_socket->SetConnectCallback(MakeNullCallback<void, Ptr<Socket>>(),
                                     MakeNullCallback<void, Ptr<Socket>>());
        m_socket->SetSendCallback(MakeNullCallback<void, Ptr<Socket>, uint32_t>());
    }
}

void
CustomTcpApp::ConnectionSucceeded(Ptr<Socket> socket)
{
    NS_LOG_INFO("CustomTcpApp conectada em t=" << Simulator::Now().GetSeconds() << "s");
    m_connected = true;
    if (m_running)
    {
        StartBlockTransfer();
    }
}

void
CustomTcpApp::ConnectionFailed(Ptr<Socket> socket)
{
    NS_LOG_WARN("CustomTcpApp falhou ao conectar em t=" << Simulator::Now().GetSeconds() << "s");
    m_connected = false;
}

void
CustomTcpApp::StartBlockTransfer()
{
    if (!m_running || !m_connected)
    {
        return;
    }

    NS_LOG_INFO("Iniciando envio de bloco de " << m_blockSize << " bytes em t="
                                               << Simulator::Now().GetSeconds() << "s");
    m_bytesRemainingInBlock = m_blockSize;
    SendChunk();
}

void
CustomTcpApp::HandleSend(Ptr<Socket> socket, uint32_t txSpace)
{
    if (m_running && m_connected && m_bytesRemainingInBlock > 0)
    {
        SendChunk();
    }
}

void
CustomTcpApp::SendChunk()
{
    while (m_running && m_connected && m_bytesRemainingInBlock > 0)
    {
        uint32_t available = m_socket->GetTxAvailable();
        if (available == 0)
        {
            // Buffer de envio cheio; HandleSend será chamado quando houver espaço.
            return;
        }

        uint32_t toSend = std::min(m_bytesRemainingInBlock, available);
        Ptr<Packet> packet = Create<Packet>(toSend);
        int sent = m_socket->Send(packet);

        if (sent <= 0)
        {
            return;
        }

        m_bytesRemainingInBlock -= static_cast<uint32_t>(sent);
        m_totalBytesSent += static_cast<uint64_t>(sent);
    }

    // Bloco de 50.000 bytes totalmente entregue ao socket TCP: agendar pausa exata de 2.0s
    if (m_running && m_bytesRemainingInBlock == 0)
    {
        m_blocksSent++;
        NS_LOG_INFO("Bloco #" << m_blocksSent << " concluído em t="
                              << Simulator::Now().GetSeconds()
                              << "s. Agendando próximo envio após pausa de "
                              << m_pauseDuration.GetSeconds() << "s.");
        m_sendEvent =
            Simulator::Schedule(m_pauseDuration, &CustomTcpApp::StartBlockTransfer, this);
    }
}

} // namespace ns3
