from mininet.topo import Topo

class MyTopo(Topo):
    def build(self):
        # Hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        # Roteadores
        r1 = self.addHost('r1')
        r2 = self.addHost('r2')
        r3 = self.addHost('r3')

        # Conexões entre hosts e roteadores
        self.addLink(h1, r1)

        self.addLink(h2, r2)
        self.addLink(h3, r2)

        self.addLink(h4, r3)

        # Conexões entre roteadores
        self.addLink(r1, r2)
        self.addLink(r2, r3)
