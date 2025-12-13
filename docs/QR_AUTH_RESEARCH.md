# Tuya QR Code Authentication - Research Analysis

## Účel dokumentu

Hloubková analýza implementace QR autentizace v **tuya-local** integraci pro budoucí implementaci do **LocalTuya 2.0 (BildaSystem fork)**.

**Status:** Pouze výzkum - bez implementace

---

## Klíčové zjištění

Tuya-local používá **tuya-device-sharing-sdk** místo standardního Tuya IoT API. Toto SDK umožňuje autentizaci bez developer účtu - stačí **User Code** z Tuya/Smart Life aplikace.

---

## 1. Autentizační flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Uživatel zadá User Code z Tuya aplikace                  │
│     (Me > Settings > Account and Security > User Code)       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. POST /v1.0/m/life/home-assistant/qrcode/tokens           │
│     Params: clientid, usercode, schema                       │
│     Returns: token (alphanumeric string)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Zobrazí QR kód s URI:                                    │
│     tuyaSmart--qrLogin?token={TOKEN}                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Uživatel naskenuje QR v Smart Life aplikaci              │
│     (NE běžná kamera - musí být Tuya app!)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Polling: GET /v1.0/m/life/home-assistant/qrcode/tokens/{token}
│     Čeká na potvrzení z Tuya serveru                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Response obsahuje: terminal_id, endpoint,                │
│     access_token, refresh_token, expiration_time             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Načtení zařízení přes Manager SDK                        │
│     → Vrátí: ID, name, local_key, IP, category              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. API Endpointy

### Base URL
```
https://apigw.iotbing.com
```

### Regionální endpointy (vráceny po autentizaci)
| Region | Endpoint |
|--------|----------|
| International | `https://apigw.iotbing.com` |
| China | `https://apigw-cn.iotbing.com` |
| Europe | `https://apigw-eu.iotbing.com` |
| USA | `https://apigw-us.iotbing.com` |

### Klíčové endpointy

**Generování QR tokenu:**
```
POST /v1.0/m/life/home-assistant/qrcode/tokens
Content-Type: application/json

{
    "clientid": "...",
    "usercode": "...",
    "schema": "..."
}
```

**Polling výsledku (po skenování):**
```
GET /v1.0/m/life/home-assistant/qrcode/tokens/{token}?clientid=...&usercode=...
```

**Response při úspěchu:**
```json
{
    "success": true,
    "result": {
        "user_code": "string",
        "terminal_id": "device_identifier",
        "endpoint": "https://apigw-{region}.iotbing.com",
        "access_token": "token_string",
        "refresh_token": "refresh_token_string",
        "expiration_time": 3600
    },
    "t": 1712188152186
}
```

---

## 3. QR Code formát

### URI Scheme
```
tuyaSmart--qrLogin?token=AZ1712188152186pKxANZZDFcNgXHxnIKSsjUamlo178365845218603
```

### Home Assistant QrCodeSelector
```python
from homeassistant.components.qr_code import QrCodeSelector, QrCodeSelectorConfig, QrErrorCorrectionLevel

vol.Optional("QR"): QrCodeSelector(
    config=QrCodeSelectorConfig(
        data=f"tuyaSmart--qrLogin?token={token}",
        scale=5,
        error_correction_level=QrErrorCorrectionLevel.QUARTILE,
    )
)
```

---

## 4. Klíčové soubory v tuya-local

### Integrace
| Soubor | Účel |
|--------|------|
| `config_flow.py` | Konfigurace, QR zobrazení, výběr zařízení |
| `cloud.py` | Cloud API wrapper (QR generace, login polling, device list) |
| `const.py` | Konstanty (hub kategorie, cloud settings) |

### SDK (tuya-device-sharing-sdk)
| Soubor | Účel |
|--------|------|
| `tuya_sharing/user.py` | `LoginControl` class - `qr_code()`, `login_result()` |
| `tuya_sharing/manager.py` | `Manager` class - device cache, home/device queries |
| `tuya_sharing/repository.py` | `DeviceRepository`, `HomeRepository` - API volání |
| `tuya_sharing/customer_api.py` | HTTP client pro Tuya API |

---

## 5. SDK Dependency

### PyPI balíček
```
tuya-device-sharing-sdk
```

### Instalace
```bash
pip install tuya-device-sharing-sdk
```

### GitHub
https://github.com/tuya/tuya-device-sharing-sdk

### Použití v kódu
```python
from tuya_sharing import Manager, LoginControl

# QR generace
login_control = LoginControl(
    root_path=".",
    client_id="...",
    user_code="...",
)
qr_token = login_control.qr_code()

# Polling po skenování
result = login_control.login_result(qr_token)

# Manager pro zařízení
manager = Manager(
    client_id=result["client_id"],
    user_code=result["user_code"],
    terminal_id=result["terminal_id"],
    end_point=result["endpoint"],
    token_info=result["token_info"]
)

# Načtení zařízení
manager.update_device_cache()
devices = manager.device_map
```

---

## 6. Data získaná o zařízeních

```python
{
    "id": "device_id",              # Unique device identifier
    "name": "device_name",          # Display name
    "category": "znyxss",           # Device category/type
    "ip": "192.168.1.100",          # Local IP (pokud dostupná)
    "local_key": "key_hash",        # Šifrovací klíč pro lokální komunikaci
    "product_id": "product_123",    # Tuya product identifier
    "online": true,                 # Online status
    "sub_ids": ["sub_1", "sub_2"]   # Sub-device IDs (pro huby)
}
```

---

## 7. Bezpečnostní aspekty

1. **Tokeny se NEUKLÁDAJÍ na disk** - pouze v paměti
2. **Session scoped** - po restartu HA nutná nová autentizace
3. **HTTPS only** - veškerá komunikace šifrovaná
4. **Local key** - přenášen pouze přes autentizovaný cloud
5. **User Code** - není ukládán, použit jen pro QR generaci

---

## 8. Rozdíly oproti naší implementaci

### Naše LocalTuya 2.0 (aktuálně)
- Vyžaduje **Tuya IoT Developer účet**
- Nutné: Client ID, Client Secret, User ID
- Komplikované pro běžné uživatele

### Tuya-local (QR auth)
- **Nevyžaduje developer účet**
- Stačí: User Code z Tuya aplikace
- Uživatelsky přívětivé

---

## 9. Možnosti implementace

### Varianta A: Přidat tuya-device-sharing-sdk jako dependency
**Pros:**
- Hotové řešení, testované
- Automatické aktualizace SDK

**Cons:**
- Další dependency
- Možné konflikty verzí

### Varianta B: Portovat relevantní kód přímo
**Pros:**
- Žádné externí závislosti
- Plná kontrola

**Cons:**
- Více práce
- Nutnost sledovat změny v API

### Varianta C: Nabídnout obě metody autentizace
**Pros:**
- Flexibilita pro uživatele
- Zpětná kompatibilita

**Cons:**
- Komplexnější UI
- Více kódu k údržbě

---

## 10. Zdroje

- [tuya-local GitHub](https://github.com/make-all/tuya-local)
- [tuya-device-sharing-sdk](https://github.com/tuya/tuya-device-sharing-sdk)
- [Tuya QR Code User Login Docs](https://developer.tuya.com/en/docs/app-development/userqrlogin?id=Ka6a99lrvq6tn)
- [HA Core PR #104767 - QR Login](https://github.com/home-assistant/core/pull/104767/files)
- [HA Community - Tuya QR Setup](https://community.home-assistant.io/t/tuya-integration-ha-2024-02-qr-code/686633)

---

## Další kroky (budoucí implementace)

1. [ ] Rozhodnout variantu implementace (A/B/C)
2. [ ] Přidat `QrCodeSelector` do `config_flow.py`
3. [ ] Implementovat cloud API pro QR endpointy
4. [ ] Přidat polling mechanismus pro login result
5. [ ] Integrovat s existující cloud sync logikou
6. [ ] Testovat s různými regiony
7. [ ] Dokumentovat pro uživatele

---

*Dokument vytvořen: 2025-12-13*
*Autor: BildaSystem.cz + Claude Code*
*Status: Research only - no implementation*
