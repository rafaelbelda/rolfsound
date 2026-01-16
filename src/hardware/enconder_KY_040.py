"""
Controle de Encoder KY-040 com Atualização AO VIVO
- Gira = muda threshold instantaneamente
- Botão = livre para função futura
"""

import time
import logging
import config

def testEncoder():
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        raise ImportError("Este módulo só pode ser executado em um Raspberry Pi com RPi.GPIO instalado.")

class EncoderControl:
    """
    Encoder rotacional que atualiza threshold em tempo real
    Sem necessidade de salvar - apenas ajuste ao vivo
    """
    
    def __init__(self, clk_pin=17, dt_pin=27, sw_pin=22, logger=None):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO

        self.logger = logger or logging.getLogger(__name__)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.sw_pin = sw_pin
        
        # Configura pinos com pull-up
        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Valores
        self.threshold = config.get("recorder")["threshold"]  # Valor inicial padrão
        self.min_threshold = config.get("recorder")["min_threshold"]
        self.max_threshold = config.get("recorder")["max_threshold"]
        self.step = config.get("recorder")["enconder_step"]  # Incremento por clique (ajustável)
        
        # Estado anterior para detecção de rotação
        self.last_clk_state = GPIO.input(self.clk_pin)
        
        # Callbacks opcionais
        self.on_change_callback = None
        self.on_button_callback = None  # Para função futura
        
        # Setup de interrupts para resposta instantânea
        try:
            GPIO.add_event_detect(
                self.clk_pin, 
                GPIO.BOTH, 
                callback=self._encoder_callback, 
                bouncetime=2  # 2ms de debounce
            )
            
            GPIO.add_event_detect(
                self.sw_pin, 
                GPIO.FALLING, 
                callback=self._button_callback, 
                bouncetime=300  # 300ms para evitar duplo clique
            )
            self.logger.info(f"Encoder inicializado nos pinos CLK={clk_pin}, DT={dt_pin}, SW={sw_pin}")
        except Exception as e:
            self.logger.error(f"Erro ao configurar encoder: {e}")
            raise
    
    def _encoder_callback(self, channel):
        """
        Chamado IMEDIATAMENTE quando encoder gira
        Atualiza threshold em tempo real
        """
        try:
            clk_state = GPIO.input(self.clk_pin)
            dt_state = GPIO.input(self.dt_pin)
            
            # Detecta apenas na borda de subida do CLK
            if clk_state != self.last_clk_state and clk_state == 1:
                # Horário (CW) = aumenta | Anti-horário (CCW) = diminui
                if dt_state != clk_state:
                    self.threshold += self.step
                else:
                    self.threshold -= self.step
                
                # Limita aos valores mín/máx
                self.threshold = max(self.min_threshold, 
                                   min(self.max_threshold, self.threshold))
                
                # Dispara callback se definido (para display, log, etc)
                if self.on_change_callback:
                    self.on_change_callback(self.threshold)
            
            self.last_clk_state = clk_state
        except Exception as e:
            self.logger.error(f"Erro no callback do encoder: {e}")
    
    def _button_callback(self, channel):
        """
        Chamado quando botão é pressionado
        Reservado para função futura
        """
        try:
            if self.on_button_callback:
                self.on_button_callback()
        except Exception as e:
            self.logger.error(f"Erro no callback do botão: {e}")
    
    def get_threshold(self):
        """Retorna valor atual do threshold"""
        return round(self.threshold, 4)
    
    def set_threshold(self, value):
        """Define threshold manualmente (útil para valor inicial)"""
        self.threshold = max(self.min_threshold, 
                           min(self.max_threshold, float(value)))
        self.logger.debug(f"Threshold definido para: {self.threshold:.4f}")
    
    def set_step(self, step):
        """Muda incremento por clique (0.001 = fino, 0.01 = grosso)"""
        self.step = float(step)
        self.logger.debug(f"Step ajustado para: {self.step}")
    
    def set_range(self, min_val, max_val):
        """Define limites mín/máx do threshold"""
        self.min_threshold = float(min_val)
        self.max_threshold = float(max_val)
        # Reaplica limites ao valor atual
        self.threshold = max(self.min_threshold, 
                           min(self.max_threshold, self.threshold))
        self.logger.debug(f"Range ajustado: {self.min_threshold:.4f} - {self.max_threshold:.4f}")
    
    def on_change(self, callback):
        """
        Define função a ser chamada quando threshold muda
        callback(new_value) será chamado instantaneamente
        """
        self.on_change_callback = callback
        self.logger.debug("Callback on_change registrado")
    
    def on_button(self, callback):
        """
        Define função para botão (função futura)
        callback() será chamado quando apertar
        """
        self.on_button_callback = callback
        self.logger.debug("Callback on_button registrado")
    
    def cleanup(self):
        """Limpa GPIO ao encerrar"""
        try:
            GPIO.cleanup()
            self.logger.info("GPIO limpo")
        except Exception as e:
            self.logger.error(f"Erro ao limpar GPIO: {e}")


# ============================================================
# EXEMPLO DE USO COM LOGGING
# ============================================================

if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("TESTE DO ENCODER - ATUALIZAÇÃO AO VIVO")
    logger.info("=" * 50)
    logger.info("Gire o encoder para ajustar o threshold")
    logger.info("Aperte o botão para testar (função futura)")
    logger.info("CTRL+C para sair")
    
    encoder = EncoderControl(logger=logger)
    
    # Callback executado INSTANTANEAMENTE ao girar
    def on_threshold_change(new_value):
        # Limpa linha e mostra novo valor
        print(f"\rThreshold: {new_value:.4f}  ", end="", flush=True)
    
    # Callback para botão (função futura)
    def on_button_press():
        logger.info(f"Botão pressionado! Threshold atual: {encoder.get_threshold():.4f}")
        logger.info("(Aqui você adiciona sua função futura)")
    
    # Conecta callbacks
    encoder.on_change(on_threshold_change)
    encoder.on_button(on_button_press)
    
    # Mostra valor inicial
    logger.info(f"Threshold inicial: {encoder.get_threshold():.4f}")
    
    try:
        # Loop infinito - encoder responde via interrupts
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print()  # Nova linha após o display
        logger.info("Encerrando...")
        encoder.cleanup()
        logger.info("Finalizado!")