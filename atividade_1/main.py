#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel

from minha_topologia import MyTopo

def run():
    topo = MyTopo()
    net = Mininet(topo=topo)
    net.start()

    print("Configuração de IPs e rotas nos hosts e roteadores...")

    # Configuração de IPs nos hosts
    h1 = net.get('h1')
    h1.setIP('192.168.1.10/24', intf='h1-eth0')
    h2 = net.get('h2')
    h2.setIP('192.168.2.10/24', intf='h2-eth0')
    h3 = net.get('h3')
    h3.setIP('192.168.3.10/24', intf='h3-eth0')
    h4 = net.get('h4')
    h4.setIP('192.168.4.10/24', intf='h4-eth0')

    # Configuração de IPs nos roteadores
    r1 = net.get('r1')
    r1.setIP('192.168.1.1/24', intf='r1-eth0')
    r1.setIP('10.0.0.1/30', intf='r1-eth1')

    r2 = net.get('r2')
    r2.setIP('192.168.2.1/24', intf='r2-eth0')
    r2.setIP('192.168.3.1/24', intf='r2-eth1')
    r2.setIP('10.0.0.2/30', intf='r2-eth2')
    r2.setIP('10.0.1.1/30', intf='r2-eth3')

    r3 = net.get('r3')
    r3.setIP('192.168.4.1/24', intf='r3-eth0')
    r3.setIP('10.0.1.2/30', intf='r3-eth1')

    # Habilitar o encaminhamento de pacotes nos roteadores
    r1.cmd('sysctl -w net.ipv4.ip_forward=1')
    r2.cmd('sysctl -w net.ipv4.ip_forward=1')
    r3.cmd('sysctl -w net.ipv4.ip_forward=1')

    # comunicação entre todas as sub-redes
    r1.cmd('ip route add 192.168.2.0/24 via 10.0.0.2')
    r1.cmd('ip route add 192.168.3.0/24 via 10.0.0.2')
    r1.cmd('ip route add 192.168.4.0/24 via 10.0.0.2')
    r1.cmd('ip route add 10.0.1.0/30 via 10.0.0.2')

    r2.cmd('ip route add 192.168.1.0/24 via 10.0.0.1')
    r2.cmd('ip route add 192.168.4.0/24 via 10.0.1.2')

    r3.cmd('ip route add 192.168.1.0/24 via 10.0.1.1')
    r3.cmd('ip route add 192.168.2.0/24 via 10.0.1.1')
    r3.cmd('ip route add 192.168.3.0/24 via 10.0.1.1')
    r3.cmd('ip route add 10.0.0.0/30 via 10.0.1.1')

    # Comunicação entre hosts e roteadores
    h1.cmd('ip route add default via 192.168.1.1')
    h2.cmd('ip route add default via 192.168.2.1')
    h3.cmd('ip route add default via 192.168.3.1')
    h4.cmd('ip route add default via 192.168.4.1')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

