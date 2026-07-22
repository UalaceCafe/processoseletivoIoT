# Relatório - Processo Seletivo – Intensivo Maker | IoT

### Identificação do Candidato

- **Nome completo:** Ualace Henrique Santos Café
- **GitHub:** [https://github.com/UalaceCafe](https://github.com/UalaceCafe)

---

## Visão Geral da Solução

O projeto tem como objetivo o desenvolvimento de uma solução embarcada para um sistema de contagem automática de itens em linhas de produção manuais ou semiautomáticas através do uso de um sensor dependente de luz (LDR) e de um botão push simples. A implementação garante que não sejam necessárias anotações por parte de terceiros e que métricas de produção possam ser fornecidas automaticamente, em tempo real.

---

## Arquitetura do Sistema Embarcado

**Fluxo principal (`main.py`):** o programa roda em um `while True` não-bloqueante, com uma espera de 20 ms entre execuções. A cada iteração, o tempo atual é obtido (`time.ticks_ms()`) e são chamados dois métodos: `check_ldr_state()` e `check_button_state()`.

**Firmware do sensor `LDR`:** o método privado `_lux()` converte a leitura bruta do ADC em uma estimativa de luminosidade, usando o modelo de resistência do fotorresistor dado na documentação do Wokwi. A tensão é limitada ao intervalo `[0.001, 3.299]` para evitar erro de domínio (divisão por zero ou exponenciação que resulta em número complexo) quando a leitura satura. A partir de `_lux()`, dois métodos públicos expõem a lógica de decisão à classe `ProductionCounter`: `is_blocked()` (lux abaixo de `low_thres`) e `is_free()` (lux acima de `high_thres`).


**Máquina de estados da esteira:**

```
FREE  --lux < 100 (objeto)-->  BLOCKED
BLOCKED  --lux > 500 (ambiente)-->  FREE  (incrementa contador)
```

As variáveis `low_thres` e `high_thres`, como mencionado anteriormente, definem quais valores de luminosidade que servem de limiar para determinar se um objeto está obstruindo o sensor (isto é, há um objeto a ser contado) ou não, respectivamente. Daí, o incremento do contador de peças ocorre na transição `BLOCKED -> FREE`, garantindo que a peça tenha passado completamente pelo sensor.

**Detecção de micro-parada:** enquanto o estado permanece `BLOCKED`, verifica-se a cada ciclo se o tempo desde que o sensor foi obstruído é maior ou igual ao tempo máximo aceito (isto é, `now - block_start >= 5000 ms`). Se sim, o alerta é emitido uma única vez (garantido pela flag `has_reported_stop`), evitando spam na saída serial.

**Reset de turno:** como requerido, um botão é usado para resetar o estado do sistema. Para garantir uma leitura confiável do mesmo, é implementado um algoritmo de debounce via software, através de uma máquina de estados independente baseada em borda + duração. É detectada a borda de subida do botão (`pressed_edge`), o tempo atual é registrado, e ao detectar a borda de descida (`released_edge`), o tempo pressionado é calculado. Assim, `_reset_shift()` (isto é, o reset de turno em si) só é executado se esse intervalo for maior que 50 ms (definido na constante `DEBOUNCE_MS`).

---

## Componentes Utilizados na Simulação

| Componente | ID | Conexões | Função |
|:-:|:-:|:-|:-|
| Placa ESP32-DevKitC V4 | esp | - | Microcontrolador principal. É nele que é implementado toda  a lógica do firmware e por onde ocorre a comunicação serial.
| Sensor dependente de luz (LDR)* | ldr1 | O sensor é alimentado através dos pinos de 3.3V e GND da ESP32; o pino analógico é conectado ao pino 13 da placa; o pino digital, ao D2, mas não é utilizado. | Como sua resistência varia de acordo com a intensidade de luz detectada, é usado para realizar a contagem das peças na esteira.
| Botão push | btn1 | O terminal 1 é conectado ao pino de 3.3V da placa; o terminal 2, ao pino 5. | É usado para resetar o estado do sistema.

Os componentes e as conexões acima também podem ser vistos no arquivo [diagram.json](diagram.json).

\* Os valores dos atributos `rl10` e `gamma`, necessários para o cálculo da resistência do LDR, foram os padrões do Wokwi, `50` e `0.7`, respectivamente.

---

## Decisões Técnicas Relevantes

O código foi organizado em duas classes com responsabilidades separadas: `LDR`, que abstrai a leitura do sensor, converte o valor do ADC em luminosidade e implementa a lógica de verificação dos limiares de luminosidade; e `ProductionCounter`, que concentra a lógica principal e as máquinas de estado. Essa divisão evita que a fórmula fotométrica se misture com as regras de contagem, facilitando manutenção e testes isolados. Alguns parâmetros, como pinos da placa utilizados, o limiar de micro-parada e o tempo de debounce foram extraídos como constantes nomeadas no topo do arquivo, em vez de números soltos no código, tornando-os fáceis de localizar e ajustar.

Os estados da esteira (`FREE`/`BLOCKED`) foram representados de forma simples, como um atributo do tipo string, o que é suficiente para uma máquina de apenas dois estados sem adicionar complexidade desnecessária. Para evitar oscilações causadas por ruído do sensor e condições variáveis de iluminação ambiente, dois limiares de luminosidade (um para "bloqueado" e outro para "livre") foram usados, em vez de um único valor de corte, criando uma histerese que estabiliza as transições de estado.

Como especificado nos requisitos, a implementação focou em manter toda a temporização de forma não-bloqueante: tanto a detecção de micro-parada quanto o debounce do botão são feitos por comparação de timestamps (via `time.ticks_diff`), sem uso de `sleep()` na lógica de detecção. Isso permite que o sensor de luz e botão o sejam verificados no mesmo laço principal, sem que um bloqueie o outro. Complementarmente, uma flag de controle garante que o alerta de micro-parada seja emitido uma única vez por ocorrência, evitando poluição da saída serial enquanto a condição persiste.

---

## Resultados Obtidos

O sistema foi validado com sucesso nos três cenários de teste do Wokwi CI. No **Cenário 1**, a sequência `lux: 800 → 50 → 800` (bloqueio de 300 ms) resultou na mensagem `"Peca detectada! Total: 1"`, confirmando que o contador só incrementa na borda de subida, após a peça passar completamente pelo sensor.

No **Cenário 2**, o sensor foi mantido em `lux: 50` por 5 segundos contínuos, disparando corretamente o alerta `"Alerta: Micro-parada detectada!"` assim que o limiar `MICRO_STOP_TIME_LIMIT_MS` (ou seja, 5s) foi atingido, validando o cálculo de tempo não-bloqueante do firmware.

No **Cenário 3**, o botão foi pressionado por 200 ms — acima do limiar de debounce de 50 ms — e o sistema respondeu com `"Turno resetado com sucesso. Contadores zerados."`, confirmando que o estado interno foi reiniciado corretamente.

Em todos os testes, as mensagens seriais corresponderam ao esperado, sem contagens duplicadas, alertas repetidos ou resets falsos. Assim, os resultados evidenciam que a estratégia adotada, baseada em polling não bloqueante, histerese de luminosidade e debounce temporal, permitiu tratar corretamente todos os cenários de estímulo definidos no CI.

---

## Comentários Adicionais

A implementação da lógica de debounce do botão de reset foi umas das dificuldades principais. Em versões anteriores, a abordagem adotada sempre causava *timeout* e leituras incorretas em um ou mais testes de CI, exigindo modificações até chegar à versão baseada em detecção de borda com medição do tempo pressionado, que se mostrou mais estável.

Como limitação, a solução assume um único objeto por vez na esteira; peças muito próximas entre si (menor que o tempo de resposta do loop) poderiam não ser distinguidas corretamente. Em revisões futuras, seria interessante adicionar um cálculo de tempo de ciclo médio entre peças e talvez persistir os dados de produção, já que atualmente tudo é perdido ao reiniciar o turno.

O maior aprendizado foi a importância da temporização não-bloqueante em sistemas embarcados: usar `time.ticks_diff()` em vez de `sleep()` para controlar lógica de estado é uma mudança simples, mas que foi essencial para manter o firmware responsivo e testável, vide o caso do debounce, que deixou isso mais evidente na prática.
