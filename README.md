# IF738 - Redes de Computadores

Repositório destinado para armazenar as atividades práticas da disciplina **IF738 - Redes de Computadores** oferecida pela universidade.

## Sobre a Disciplina

IF738 é uma cadeira fundamental no curso de Engenharia de Computação que aborda os conceitos essenciais de redes de computadores, incluindo arquitetura de redes, protocolos de comunicação, roteamento, comutação e simulação de topologias de rede.

---

## 📚 Atividades

### Atividade 1: Topologia de Rede com Mininet

**Objetivo:** Criar e configurar uma topologia de rede complexa utilizando o Mininet, com múltiplos roteadores e sub-redes, garantindo comunicação entre todos os hosts através de roteamento estático.

**Descrição:**
- Implementação de uma topologia com **4 hosts** (h1, h2, h3, h4) e **3 roteadores** (r1, r2, r3)
- Configuração de **4 sub-redes (LANs)** interconectadas via roteadores
- Atribuição de endereçamento IP em cada dispositivo
- Configuração de **roteamento estático** para garantir conectividade entre todas as sub-redes
- Validação da comunicação entre hosts em redes diferentes através de testes de ping

**Arquivos:**
- `main.py` - Script principal que executa a simulação
- `minha_topologia.py` - Definição da topologia de rede
- `relatorio.md` - Documentação detalhada da atividade com imagens

**Tecnologias:** Mininet, Python, Linux
