# LocalTuya Bildass - Issue Tracking

## Aktuální problém: Protocol 3.5 Session Negotiation Failure

### Zařízení: Switch-Satna
- **Device ID:** `bfc42749075549ec91bqsx`
- **Custom Name:** Switch-Satna
- **Local Key:** `7{OVAMlo60N$H)z/` (POZOR: speciální znaky!)
- **Product Name:** WIFI 智能开关 (WiFi Smart Switch / Circuit Breaker)
- **Product ID:** `mnrs7adp4kp6y5pa`
- **Category:** dlq (circuit breaker)
- **Protocol:** 3.5 (v3.5)
- **Local IP:** `192.168.0.42` ✓ (zjištěno z routeru)
- **WAN IP (z Tuya Cloud):** 85.193.1.147 (normální - NAT)
- **Data Center:** Central Europe
- **Tuya Account:** Medovejkolac@gmail.com
- **Sub-device:** Ne
- **Online:** Ano (v Tuya Cloud)

#### Tuya IoT Platform API Response
```json
{
  "id": "bfc42749075549ec91bqsx",
  "custom_name": "Switch-Satna",
  "local_key": "7{OVAMlo60N$H)z/",
  "product_name": "WIFI 智能开关",
  "product_id": "mnrs7adp4kp6y5pa",
  "category": "dlq",
  "is_online": true,
  "sub": false,
  "ip": "85.193.1.147"
}
```

### Symptomy
```
session key negotiation failed on step 1
Command 3 timed out waiting for sequence number -102
received null payload (None) but out of recv retries
```

### Root Cause
Protocol 3.5 používá:
- Prefix `6699` místo `55aa`
- GCM šifrování místo ECB
- Jiný session key negotiation algorithm

Současná implementace Protocol 3.5 v localtuya_bildass NEFUNGUJE - session negotiation timeout.

### Co bylo opraveno (v6.3.0)
- [x] status() vrací raw response místo dps_cache
- [x] detect_available_dps() správně zpracovává response
- [x] Přidán Protocol 3.5 do selectoru
- [x] Lepší logging

### Co bylo opraveno (v6.3.1)
- [x] Protocol 3.5 session key negotiation - používá 55AA prefix místo 6699
- [x] Protocol 3.5 session negotiation používá ECB šifrování jako 3.4
- [x] Použití real_local_key pro session negotiation HMAC

### Aktuální stav (2025-12-10 13:30)
- [x] v6.3.1 fix je aplikován (log ukazuje "v3.5 session negotiation using 55AA/ECB format")
- [ ] Zařízení NEODPOVÍDÁ na session negotiation - timeout na seq -102
- [ ] Zařízení NENÍ v UDP discovery (ostatní zařízení ano: 192.168.0.27, .35, .38, .40, .41, .43)
- [ ] **NUTNO ZJISTIT LOCAL IP** - z routeru nebo Fing app

### UDP Discovery - fungující zařízení
```
Device bf85944453163c23365ay7 found with IP 192.168.0.27
Device bff98d68bbdd3a419bwc68 found with IP 192.168.0.35
Device bf9f6a837466be612b03cn found with IP 192.168.0.41
Device bfe9fe32464ed4ede16ttm found with IP 192.168.0.38
```
Switch-Satna (`bfc42749075549ec91bqsx`) CHYBÍ v tomto seznamu!

### Možné příčiny
1. **Špatná lokální IP** - zařízení může mít jinou IP než si LocalTuya myslí
2. **Firewall/izolace** - zařízení může být na jiném subnetu nebo blokované
3. **Špatný local_key** - ověřit že `7{OVAMlo60N$H)z/` je správně zadaný (speciální znaky!)
4. **Špatný protokol** - zkusit Protocol 3.4 nebo 3.3 místo 3.5

### Co je potřeba udělat
- [x] Zjistit LOCAL IP z routeru → **192.168.0.42**
- [ ] Ověřit že local_key je správně zadaný v LocalTuya
- [ ] Zkusit Protocol 3.4 místo 3.5
- [ ] Zkusit Protocol 3.3 (úplně přeskočí session negotiation)
- [ ] **NOVÉ v6.3.2:** Použít "Skip Connection Check" option

### Co bylo opraveno (v6.3.2)
- [x] Nová option: Skip Connection Check - přeskočí connection test úplně
- [x] Přidán Protocol 3.5 do options_schema (chyběl)
- [x] Když skip_connect je zapnutý, použije Manual DPS nebo default DPS 1

### Reference
- xZetsubou fork: https://github.com/xZetsubou/hass-localtuya
- Protocol 3.5 docs: https://limbenjamin.com/articles/tuya-local-and-protocol-35-support.html

### Log ukázka
```
2025-12-10 12:49:57.282 DEBUG session key negotiation failed on step 1
2025-12-10 12:49:57.283 DEBUG Sending command 9 (device type: v3.5)
```

---

## Historie oprav

### v6.3.0 (2025-12-10)
- Fix: status() vracela dps_cache místo raw response (kritický bug)
- Fix: detect_available_dps() dead code opraveno
- Add: Protocol 3.5 v selectoru
- Add: Lepší debug logging

### v6.2.0 (2025-12-10)
- Add: Heartbeat wake-up před DPS detekcí
- Add: Retry mechanismus s exponential backoff
- Add: Force Add option
