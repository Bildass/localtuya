#!/usr/bin/env python3
"""
Diagnostika Switch-Satna - spusť na HA nebo zařízení na stejné LAN!
"""
import socket
import struct
import hashlib
from Crypto.Cipher import AES

# Switch-Satna config
DEVICE_IP = "192.168.0.42"
DEVICE_ID = "bfc42749075549ec91bqsx"
LOCAL_KEY = "7{OVAMlo60N$H)z/"  # POZOR: speciální znaky!
PORT = 6668

def pad(data):
    padnum = 16 - len(data) % 16
    return data + bytes([padnum] * padnum)

def encrypt(data, key):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return cipher.encrypt(pad(data))

print("=" * 60)
print("DIAGNOSTIKA SWITCH-SATNA")
print("=" * 60)

# Test 1: Ping (TCP connect)
print(f"\n[1] TCP spojení na {DEVICE_IP}:{PORT}...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((DEVICE_IP, PORT))
    if result == 0:
        print(f"    ✅ Port {PORT} je OTEVŘENÝ - zařízení odpovídá!")
    else:
        print(f"    ❌ Port {PORT} je ZAVŘENÝ (error: {result})")
        print("    → Zařízení možná nemá local API nebo je offline")
    sock.close()
except Exception as e:
    print(f"    ❌ Chyba: {e}")

# Test 2: Zkusíme i port 6666 a 6667 (UDP discovery)
print(f"\n[2] Kontrola UDP discovery portů...")
for port in [6666, 6667]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.bind(('', port))
        print(f"    Naslouchám na UDP {port}...")
        try:
            data, addr = sock.recvfrom(1024)
            print(f"    ✅ Přijata data z {addr}")
        except socket.timeout:
            print(f"    ⚠️  Žádná UDP broadcast data na portu {port}")
        sock.close()
    except Exception as e:
        print(f"    ❌ Port {port}: {e}")

# Test 3: Local key analýza
print(f"\n[3] Analýza Local Key...")
print(f"    Key: {LOCAL_KEY}")
print(f"    Délka: {len(LOCAL_KEY)} znaků (mělo by být 16)")
print(f"    Hex: {LOCAL_KEY.encode().hex()}")
special_chars = [c for c in LOCAL_KEY if not c.isalnum()]
if special_chars:
    print(f"    ⚠️  SPECIÁLNÍ ZNAKY: {special_chars}")
    print(f"    → Tyto znaky mohou způsobit problémy s escapováním!")

# Test 4: Zkusíme raw Tuya handshake
print(f"\n[4] Raw Tuya handshake test...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((DEVICE_IP, PORT))

    # Tuya protocol prefix
    PREFIX = b'\x00\x00\x55\xaa'

    # Simple status request (command 10)
    payload = b'{"gwId":"' + DEVICE_ID.encode() + b'","devId":"' + DEVICE_ID.encode() + b'"}'

    # Encrypt if needed
    encrypted = encrypt(payload, LOCAL_KEY[:16] if len(LOCAL_KEY) >= 16 else LOCAL_KEY.ljust(16, '\0'))

    # Build message
    seq = 1
    cmd = 10  # DP_QUERY

    # Header: prefix(4) + seq(4) + cmd(4) + len(4)
    msg = PREFIX
    msg += struct.pack('>I', seq)
    msg += struct.pack('>I', cmd)
    msg += struct.pack('>I', len(encrypted) + 8)  # +8 for CRC and suffix
    msg += encrypted

    # CRC32
    crc = struct.pack('>I', 0)  # Simplified - no real CRC
    msg += crc

    # Suffix
    msg += b'\x00\x00\xaa\x55'

    print(f"    Odesílám {len(msg)} bytů...")
    sock.send(msg)

    # Wait for response
    sock.settimeout(5)
    response = sock.recv(1024)
    if response:
        print(f"    ✅ Odpověď: {len(response)} bytů")
        print(f"    Hex (prvních 64): {response[:64].hex()}")
        if b'\x55\xaa' in response:
            print(f"    → Vypadá jako validní Tuya response!")
        else:
            print(f"    → Neznámý formát response")
    else:
        print(f"    ❌ Žádná odpověď")

    sock.close()
except socket.timeout:
    print(f"    ❌ TIMEOUT - zařízení neodpovídá na Tuya protokol")
except Exception as e:
    print(f"    ❌ Chyba: {e}")

print("\n" + "=" * 60)
print("ZÁVĚR:")
print("=" * 60)
print("""
Pokud port 6668 je ZAVŘENÝ:
  → Zařízení nemá aktivní LOCAL API
  → Zkus ho restartovat (vypnout/zapnout jistič)
  → Nebo firmware nepodporuje local control

Pokud port je OTEVŘENÝ ale timeout na handshake:
  → Špatný LOCAL KEY (zkontroluj speciální znaky)
  → Špatný PROTOCOL VERSION
  → Firmware bug

Pokud dostaneš response:
  → Zařízení funguje, problém je v LocalTuya konfiguraci
""")
