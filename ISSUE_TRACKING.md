# LocalTuya Bildass - Issue Tracking

## Aktuální problém: Protocol 3.5 Session Negotiation Failure

### Zařízení
- **Device ID:** `bfc42749075549ec91bqsx`
- **Protocol:** 3.5 (v3.5)
- **IP:** (nutno zjistit)

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

### Co je potřeba otestovat
- [ ] Protocol 3.5 zařízení - session negotiation
- [ ] DPS detekce po úspěšné session negotiation

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
