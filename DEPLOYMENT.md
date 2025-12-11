# LocalTuya Bildass - Deployment Guide

## Stav Refaktoringu

**Verze:** 10.0.0 (Kompletní refaktoring pytuya modulu)

### Dokončené Fáze

| Fáze | Soubor | Stav |
|------|--------|------|
| 1 | `pytuya/constants.py` | ✅ |
| 2 | `pytuya/cipher.py` | ✅ |
| 3 | `pytuya/message.py` | ✅ |
| 4 | `pytuya/protocol.py` | ✅ |
| 5 | `pytuya/session.py` | ✅ KRITICKÁ - Session Key Fix |
| 6 | `pytuya/transport.py` | ✅ |
| 7 | `pytuya/__init__.py` | ✅ |
| 8 | `discovery.py` | ✅ |

### Testované Funkce

- ✅ AES-ECB šifrování (Protocol 3.1-3.4)
- ✅ AES-GCM šifrování (Protocol 3.5)
- ✅ Session Key Negotiation v3.4 (ECB)
- ✅ Session Key Negotiation v3.5 (GCM) - **HLAVNÍ FIX**
- ✅ Message pack/unpack 55AA format
- ✅ Message pack/unpack 6699 format
- ✅ Protocol auto-detection

---

## Deployment do Home Assistant

### Metoda 1: Ruční Kopírování

```bash
# Na HA serveru (nebo přes SSH):
cd /config/custom_components

# Záloha původní integrace
mv localtuya_bildass localtuya_bildass.backup

# Kopírování nové verze
scp -r user@vps:/home/core/projects/localtuya/custom_components/localtuya_bildass ./

# Restart Home Assistant
ha core restart
# nebo: systemctl restart home-assistant@homeassistant.service
```

### Metoda 2: Rsync (doporučeno)

```bash
# Z VPS na HA server:
rsync -avz --delete \
  /home/core/projects/localtuya/custom_components/localtuya_bildass/ \
  ha-server:/config/custom_components/localtuya_bildass/

# Restart HA
ssh ha-server "ha core restart"
```

### Metoda 3: Git

```bash
# Na HA serveru:
cd /config
git clone https://github.com/YOUR_REPO/localtuya-bildass.git custom_components/localtuya_bildass
```

---

## Testování po Deploymentu

### 1. Zkontroluj Logy

```bash
# HA logy pro localtuya
grep localtuya /config/home-assistant.log | tail -50

# Nebo přes HA API:
ha logs | grep localtuya
```

### 2. Přidej Switch-Satna

1. Jdi do **Settings → Devices & Services → Add Integration**
2. Hledej **LocalTuya Bildass**
3. Zadej údaje:
   - **Device ID:** `bfc42749075549ec91bqsx`
   - **Local Key:** `7{OVAMlo60N$H)z/`
   - **IP Address:** `192.168.0.42`
   - **Protocol Version:** `3.5`

### 3. Očekávaný Výstup v Logu

**ÚSPĚCH:**
```
[localtuya] Connecting to bfc427...91bqsx at 192.168.0.42
[localtuya] Session key negotiation step 1: local_nonce=...
[localtuya] Session key negotiation step 2: remote_nonce=..., received_hmac=...
[localtuya] HMAC verification passed
[localtuya] Calculated session key: ...
[localtuya] Session key negotiation completed successfully
[localtuya] Connected to bfc427...91bqsx
```

**SELHÁNÍ (starý problém):**
```
session key negotiation failed on step 1
Command 3 timed out waiting for sequence number -102
```

---

## Rollback

Pokud nová verze nefunguje:

```bash
# Na HA serveru:
cd /config/custom_components
rm -rf localtuya_bildass
mv localtuya_bildass.backup localtuya_bildass
ha core restart
```

---

## Klíčové Změny v Protocol 3.5 Session Key

### Původní Problém

Session key se počítal špatně - buď se používal celý GCM output včetně IV/tag, nebo se XOR dělal špatně.

### Fix v `session.py`

```python
def calculate_session_key(self) -> bytes:
    # XOR nonces
    xor_result = bytes([a ^ b for a, b in zip(self.local_nonce, self.remote_nonce)])

    if self.version >= 3.5:
        # Protocol 3.5: GCM encrypt
        iv = self.local_nonce[:12]  # First 12 bytes of LOCAL nonce
        _, ciphertext, _ = cipher.encrypt_gcm(xor_result, iv, None)
        session_key = ciphertext[:16]  # ONLY ciphertext, no IV/tag!

        # TinyTuya validation
        if session_key[0] == 0x00:
            raise SessionKeyInvalidError("Session key starts with 0x00")

        return session_key
```

### Reference

- TinyTuya: https://github.com/jasonacox/tinytuya
- Discussion: https://github.com/jasonacox/tinytuya/discussions/260

---

## Kontakt

- **Projekt:** LocalTuya Bildass Fork
- **Maintainer:** BildaSystem.cz
