import machine, esp32, time

pin = machine.Pin(4, machine.Pin.OUT, value=0)
rmt = esp32.RMT(0, pin=pin, clock_div=80, tx_carrier=(38000, 33, 1))

CODES = {
    'POWER': 0xCC1D00FF,
    'PLAY1': 0xCC1D21DE,
    'MUTE':  0xCC1D22DD,
    'RET':   0xCC1D01FE,
    '1':     0xCC1D11EE,
    '2':     0xCC1D12ED,
    '3':     0xCC1D13EC,
    '4':     0xCC1D14EB,
    '5':     0xCC1D15EA,
    '6':     0xCC1D16E9,
    '7':     0xCC1D17E8,
    '8':     0xCC1D18E7,
    '9':     0xCC1D19E6,
    '0':     0xCC1D10EF,
    'C_F':   0xCC1D1BE4,
    'DIM':   0xCC1D1AE5,
    'DISP':  0xCC1D09F6,
    'CD_SET':0xCC1D08F7,
    'ST':    0xCC1D06F9,
    'UP':    0xCC1D03FC,
    'T_SET': 0xCC1D07F8,
    'CSET':  0xCC1D02FD,
    'ALSET': 0xCC1D05FA,
    'MODE':  0xCC1D04FB,
    'AL_ON': 0xCC1D20DF,
    '+':     0xCC1D29D6,
    '-':     0xCC1D2AD5,
    'DOWN':  0xCC1D0AF5,
    'A1':    0xCC1D24DB,
    'A2':    0xCC1D25DA,
    'A3':    0xCC1D26D9,
    'A++':   0xCC1D2BD4,
    'FLASH': 0xCC1D23DC,
    'FULL':  0xCC1D27D8,
    'SOUND': 0xCC1D28D7,
    'PLAY2': 0xCC1D40BF
}

def digit_code(d):
    digits = [0xCC1D10EF, 0xCC1D11EE, 0xCC1D12ED, 0xCC1D13EC, 0xCC1D14EB,
              0xCC1D15EA, 0xCC1D16E9, 0xCC1D17E8, 0xCC1D18E7, 0xCC1D19E6]
    return digits[d % 10]

def make_nec_hw(hex_val):
    bytes_val = [(hex_val >> 24) & 0xFF, (hex_val >> 16) & 0xFF, (hex_val >> 8) & 0xFF, hex_val & 0xFF]
    pulses = [9000, 4500]
    for b in bytes_val:
        for i in range(8):
            bit = (b >> i) & 1
            pulses.append(560)
            pulses.append(1690 if bit else 560)
    pulses.append(560)
    return pulses

def send(hex_val):
    p = make_nec_hw(hex_val)
    rmt.write_pulses(p, 1)
    rmt.wait_done()

def return_to_clock():
    send(CODES['RET'])
    print('Returned to clock display (RET)')

def countdown(minutes=1, seconds=0):
    """
    Configura e inicia un temporizador de cuenta regresiva en el reloj CHKOSDA.
    Programa exactamente los minutos y segundos solicitados (Días=000, Horas=00, Minutos=MM, Segundos=SS).
    Respeta estrictamente la ventana de 2.2s en todos los campos (incluyendo Segundos antes de PLAY1)
    para que JAMÁS rechace PLAY1 ni salte a horas o minutos erróneos.
    """
    prog_m = minutes % 100
    prog_s = seconds % 60
    
    print('Programando reloj físico para {:02d}:{:02d}...'.format(prog_m, prog_s))
    t0 = time.ticks_ms()

    # 1. Asegurar pantalla de reloj normal
    send(CODES['RET'])
    time.sleep_ms(700)

    # 2. Doble pulsación CD SET en rápida sucesión
    send(CODES['CD_SET'])
    time.sleep_ms(180)
    send(CODES['CD_SET'])
    time.sleep_ms(500)

    # 3. MODE 1 (Días: 3 dígitos -> 000) + ventana de 2.1s
    send(CODES['MODE'])
    time.sleep_ms(500)
    send(digit_code(0)); time.sleep_ms(180)
    send(digit_code(0)); time.sleep_ms(180)
    send(digit_code(0)); time.sleep_ms(2100)

    # 4. MODE 2 (Horas: 2 dígitos -> 00) + ventana de 2.1s
    send(CODES['MODE'])
    time.sleep_ms(500)
    send(digit_code(0)); time.sleep_ms(180)
    send(digit_code(0)); time.sleep_ms(2100)

    # 5. MODE 3 (Minutos: 2 dígitos -> MM) + ventana de 2.1s
    send(CODES['MODE'])
    time.sleep_ms(500)
    m_dec = (prog_m % 100) // 10
    m_uni = prog_m % 10
    send(digit_code(m_dec)); time.sleep_ms(180)
    send(digit_code(m_uni)); time.sleep_ms(2100)

    # 6. MODE 4 (Segundos: 2 dígitos -> SS) + ventana de 2.2s
    # CRÍTICO: La ventana de 2.2s DEBE esperarse también en Segundos antes de PLAY1,
    # de lo contrario el reloj ignora PLAY1 por tener la entrada abierta y cancela los segundos!
    send(CODES['MODE'])
    time.sleep_ms(500)
    s_dec = (prog_s % 60) // 10
    s_uni = prog_s % 60
    send(digit_code(s_dec)); time.sleep_ms(180)
    send(digit_code(s_uni)); time.sleep_ms(2200)

    # 7. Iniciar con PLAY
    send(CODES['PLAY1'])
    t_elapsed = time.ticks_diff(time.ticks_ms(), t0)
    print('Countdown {:02d}:{:02d} INICIADO con éxito en {} ms!'.format(prog_m, prog_s, t_elapsed))
