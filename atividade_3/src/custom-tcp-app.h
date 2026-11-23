#ifndef CUSTOM_TCP_APP_H
#define CUSTOM_TCP_APP_H

#include "ns3/address.h"
#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/socket.h"
#include "ns3/traced-callback.h"

namespace ns3
{

/**
 * \brief Aplicação TCP customizada herdando de ns3::Application.
 *
 * Envia blocos de tamanho configurável (padrão: 50.000 Bytes) via socket TCP,
 * seguidos de uma pausa de duração exata (padrão: 2.0 segundos) agendada
 * obrigatoriamente com Simulator::Schedule. O ciclo se repete até o fim da simulação.
 */
class CustomTcpApp : public Application
{
  public:
    static TypeId GetTypeId();

    CustomTcpApp();
    ~CustomTcpApp() override;

    /**
     * \brief Configura os parâmetros da aplicação.
     * \param peerAddress Endereço IP e porta do servidor/receptor de destino.
     * \param blockSize Tamanho de cada bloco em bytes (padrão: 50000).
     * \param pauseDuration Duração da pausa entre blocos (padrão: 2.0s).
     */
    void Setup(Address peerAddress,
               uint32_t blockSize = 50000,
               Time pauseDuration = Seconds(2.0));

    /**
     * \brief Retorna o socket TCP subjacente (útil para conectar traces de cwnd/RTT).
     */
    Ptr<Socket> GetSocket() const;

    /**
     * \brief Retorna o total de bytes enviados com sucesso ao socket TCP.
     */
    uint64_t GetTotalBytesSent() const;

    /**
     * \brief Retorna o número total de blocos completos enviados.
     */
    uint32_t GetBlocksSent() const;

  protected:
    void DoDispose() override;

  private:
    void StartApplication() override;
    void StopApplication() override;

    void ConnectionSucceeded(Ptr<Socket> socket);
    void ConnectionFailed(Ptr<Socket> socket);
    void HandleSend(Ptr<Socket> socket, uint32_t txSpace);

    void StartBlockTransfer();
    void SendChunk();

    Ptr<Socket> m_socket;
    Address m_peer;
    uint32_t m_blockSize;
    Time m_pauseDuration;
    uint32_t m_bytesRemainingInBlock;
    uint64_t m_totalBytesSent;
    uint32_t m_blocksSent;
    bool m_running;
    bool m_connected;
    EventId m_sendEvent;
};

} // namespace ns3

#endif // CUSTOM_TCP_APP_H
