from machine import ADC, Pin

# https://docs.wokwi.com/parts/wokwi-photoresistor-sensor
class LDR:
    def __init__(self, pin, rl10=50, gamma=0.7, low_thres=100, high_thres=500):
        self.adc = ADC(Pin(pin))
        self.rl10 = rl10
        self.gamma = gamma
        self.low_thres = low_thres
        self.high_thres = high_thres

        self.adc.atten(ADC.ATTN_11DB)

    def lux(self):
        voltage = (self.adc.read() * 5) / 1024.0
        res = 2000 * voltage / (1 - voltage / 5)
        return (self.rl10 * 1e3 * (10**self.gamma) / res)**(1.0 / self.gamma)

    def is_blocked(self):
        return self.lux() < self.low_thres

    def is_free(self):
        return self.lux() > self.high_thres
