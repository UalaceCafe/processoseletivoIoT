from machine import Pin
import time

from . import ldr

LDR_ANALOG_PIN = 13
BUTTON_PIN = 5

MICRO_STOP_TIME_LIMIT_MS = 5000
DEBOUNCE_MS = 50

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
        # Debounce and reset state
        cur = self.button.value()
        if cur != self.last_button_state:
            self.last_button_state = cur
            self.last_button_change = now

        if cur == 1:
            if time.tickes_diff(now, self.last_button_change) >= DEBOUNCE_MS:
                self.piece_counter = 0
                self.block_start = None
                self.has_reported_stop = False
                self.state = "FREE"

                print("Turno resetado com sucesso. Contadores zerados.")

                while(button.value()):
                    time.sleep(10)

                self.last_button_state = 0
                self.last_button_change = time.ticks_ms()


if __name__ == "__main__":
    ldr = LDR(LDR_ANALOG_PIN)
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
    prod_ct = ProductionCounter(ldr, button)

    while True:
        now = time.ticks_ms()
        prod_ct.check_ldr_state(now)
        prod_ct.check_button_state(now)

        time.sleep(20)
