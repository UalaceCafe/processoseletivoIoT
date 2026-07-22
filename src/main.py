from machine import Pin, ADC
import time

LDR_ANALOG_PIN = 13
BUTTON_PIN = 5

MICRO_STOP_TIME_LIMIT_MS = 5000
DEBOUNCE_MS = 50

# https://docs.wokwi.com/parts/wokwi-photoresistor-sensor
class LDR:
    def __init__(self, pin, rl10=50, gamma=0.7, low_thres=100, high_thres=500):
        self.adc = ADC(Pin(pin))
        self.rl10 = rl10
        self.gamma = gamma
        self.low_thres = low_thres
        self.high_thres = high_thres

        self.adc.atten(ADC.ATTN_11DB)

    def is_blocked(self):
        return self._lux() < self.low_thres

    def is_free(self):
        return self._lux() > self.high_thres

    def _lux(self):
        voltage = (self.adc.read() * 3.3) / 4095.0
        # Clamp voltage to [0.001, 3.299] to avoid noisy readings that may cause a domain error in the lux calculation
        voltage = min(max(voltage, 0.001), 3.299)
        res = 2000 * voltage / (1 - voltage / 3.3)
        return (self.rl10 * 1e3 * (10**self.gamma) / res)**(1.0 / self.gamma)

class ProductionCounter:
    # A. Inicialização do Sistema
    def __init__(self, ldr, button):
        # Hardware
        self.ldr = ldr
        self.button = button

        # State variables
        self.piece_counter = 0
        self.state = "FREE"
        self.block_start = None
        self.has_reported_stop = False
        self.last_button_state = self.button.value()
        self.last_button_change = time.ticks_ms()

        print("Contador de Producao Inicializado")

    # B. Lógica de Detecção e Contagem de Peças
    # C. Lógica de Detecção de Micro-paradas
    def check_ldr_state(self, now):
        if self.state == "FREE":
            if self.ldr.is_blocked():
                self.state = "BLOCKED"
                self.block_start = now
                self.has_reported_stop = False
        elif self.state == "BLOCKED":
            if not self.has_reported_stop:
                if time.ticks_diff(now, self.block_start) >= MICRO_STOP_TIME_LIMIT_MS:
                    print("Alerta: Micro-parada detectada!")
                    self.has_reported_stop = True

            if self.ldr.is_free():
                self.piece_counter += 1
                print(f"Peca detectada! Total: {self.piece_counter}")

                self.state = "FREE"

    # D. Rotina de Reset de Turno
    def check_button_state(self, now):
        cur = self.button.value()
        pressed_edge = (cur == 1 and self.last_button_state == 0)
        released_edge = (cur == 0 and self.last_button_state == 1)
        self.last_button_state = cur

        if pressed_edge:
            self.last_button_change = now

        if released_edge and self.last_button_change is not None:
            held_ms = time.ticks_diff(now, self.last_button_change)
            self.last_button_change = None
            if held_ms >= DEBOUNCE_MS:
                self._reset_shift()

    def _reset_shift(self):
        self.piece_counter = 0
        self.block_start = None
        self.has_reported_stop = False
        self.state = "FREE"

        print("Turno resetado com sucesso. Contadores zerados.")

if __name__ == "__main__":
    ldr = LDR(LDR_ANALOG_PIN)
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
    prod_ct = ProductionCounter(ldr, button)

    while True:
        now = time.ticks_ms()
        prod_ct.check_ldr_state(now)
        prod_ct.check_button_state(now)

        time.sleep_ms(20)
