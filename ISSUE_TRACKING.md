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

### Aktuální stav (2025-12-10 večer)
- [x] **POTVRZENO:** Switch-Satna ENTITA NEEXISTUJE v Home Assistant!
- [x] Hledáno v HA API: `switch_satna`, `bfc42749`, `circuit`, `dlq`, `breaker` - žádné výsledky
- [x] LocalTuya Bildass integrace je načtená (11 zařízení, 61 entit) - ale Switch-Satna NENÍ mezi nimi
- [x] Zařízení nebylo nikdy úspěšně přidáno kvůli Protocol 3.5 session negotiation failure
- [ ] **IP adresa se možná změnila** - byl IP konflikt s RGBW šatna na 192.168.0.42
- [ ] Nutno zjistit novou IP z MikroTik routeru
- [ ] Po zjištění IP zkusit přidat znovu s Protocol 3.4 nebo 3.3

### HA MCP Server vytvořen
- Cesta: `/home/core/mcp-servers/ha/`
- Konfigurace: `/home/core/.config/claude-code/mcp.json`
- **Po restartu Claude Code bude dostupný** pro přímou komunikaci s HA API
- Tools: `ha_get_state`, `ha_get_states`, `ha_call_service`, `ha_reload_integration`, `ha_get_config`, `ha_check_connection`, `ha_get_integrations`, `ha_get_device_registry`

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

### Co bylo opraveno (v7.0.0) - MAJOR REFAKTORING
**Kompletní přepsání pytuya modulu podle TinyTuya reference**

Nová modulární architektura:
- `pytuya/constants.py` - všechny konstanty a error codes
- `pytuya/cipher.py` - AES-ECB a AES-GCM šifrování (explicitní metody)
- `pytuya/message.py` - TuyaMessage, MessagePayload dataclasses
- `pytuya/protocol.py` - pack/unpack pro 55AA a 6699 formáty
- `pytuya/session.py` - **SessionKeyNegotiator** (KRITICKÝ FIX!)
- `pytuya/transport.py` - refaktorovaný TuyaProtocol

**Klíčový fix v session.py:**
```python
def calculate_session_key(self):
    xor_result = bytes([a ^ b for a, b in zip(self.local_nonce, self.remote_nonce)])

    if self.version >= 3.5:
        iv = self.local_nonce[:12]  # CORRECT: Use LOCAL nonce
        _, ciphertext, _ = cipher.encrypt_gcm(xor_result, iv, None)
        session_key = ciphertext[:16]  # CORRECT: Only ciphertext!

        if session_key[0] == 0x00:
            raise SessionKeyInvalidError("Session key starts with 0x00")
        return session_key
```

Opravené problémy:
- [x] Session key se počítal špatně (používal celý GCM output včetně IV/tag)
- [x] Přidána validace session key (nesmí začínat 0x00 - TinyTuya requirement)
- [x] HMAC verification s proper error handling
- [x] Discovery.py zjednodušen - používá cipher modul
- [x] Backward compatible API v pytuya/__init__.py

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


DEBUG!!!
2025-12-10 22:08:06.941 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] Raw 6699 data from ('192.168.0.42', 59727): 0000669900000000000000000013000000d50cb3190adef57e270f966583b4bc35e02535604a59d5 (len=235)
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] Received 6699 format broadcast from ('192.168.0.42', 59727), payload len: 213, payload start: 0cb3190adef57e270f966583b4bc35e02535604a59d55774
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] ECB with UDP_KEY failed: The length of the provided data is not a multiple of the block length.
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] ECB with UDP_KEY_35 failed: The length of the provided data is not a multiple of the block length.
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] GCM attempt: iv=0cb3190adef57e270f966583, tag=3e48ddd2bc642d8618afb74df09904f8, encrypted_len=185
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] GCM without AAD failed: 
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] GCM with finalize_with_tag failed: 
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] GCM alt IV position failed: 
2025-12-10 22:08:06.942 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] CTR decryption also failed: 'utf-8' codec can't decode byte 0x8f in position 1: invalid start byte
2025-12-10 22:08:06.943 DEBUG (MainThread) [custom_components.localtuya_bildass.discovery] Failed to decrypt 6699 broadcast from ('192.168.0.42', 59727): All decryption methods failed for 6699 broadcast

RADY OD GPT:
✅ Správný Tuya v3.5 session-key algorithm (ověřeno podle leaků i reverzů)
1. XOR NONCE
tmp = XOR(local_nonce, remote_nonce)
2. AES-GCM encrypt (NOT ECB!)
key = device_key (16 bytes raw, ne hex string!)
iv = local_nonce[:12]
AAD = žádné
plaintext = tmp
ciphertext length = 16 B
tag length = 16 B
výsledný blok = iv(12) + ciphertext(16) + tag(16)
→ 44 bytes

session_key = encrypted[12:28]
přesně jak říkáš.

‼️ Tag a IV se do key neberou. Jen čistý ciphertext.

🧩 Proč to teď funguje lépe?
Ty jsi XOR→ECB→16B ciphertext posílal zařízení → zařízení to vezme, ale pak:

začne tvořit GCM tag pro DP_QUERY,

použije svůj session_key = GCM(tmp, iv) → ciphertext[12:28],

tvůj session_key je jiný →
GCM tag mismatch → device disconnect.

Proto:

Session negotiation OK

HEART_BEAT / DP_QUERY disconnect after ~20ms
(= čas na decrypt + GCM verify, fail → socket close)

🛠 Co teď udělat v kódu (patch)
Zajisti, že místo ECB děláš:

python
Zkopírovat kód
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

aesgcm_cipher = Cipher(
    algorithms.AES(self.real_local_key),
    modes.GCM(self.local_nonce[:12]),
    backend=default_backend()
)
encryptor = aesgcm_cipher.encryptor()

encrypted = encryptor.update(xor_result) + encryptor.finalize()

# session key = ciphertext only
session_key = encrypted[:16]

A pak:
ini
Zkopírovat kód
finish_payload = hmac + session_key
(Žádné IV, žádné tagy, žádné base64.)

🔍 Jak poznám, že to je správně?
V logu při decryptu DP_QUERY/HEARTBEAT se objeví:

powershell
Zkopírovat kód
GCM tag OK

a hlavně:
pgsql
Zkopírovat kód
Connection lost: None

Co z logů plyne (shrnutí)

Negotiation fysicky proběhl: dekryptoval se payload GCM, vyextrahoval remote_nonce a vypočítal se ECB session key 94af....

Ale log ukazuje session key negotiation step 2 HMAC mismatch (may be ok for some devices) — tj. zařízení odeslalo HMAC, který se liší od toho, co tvůj kód očekává (wanted=0892... but got=6969...).

Kód přesto pokračuje, posílá SESS_KEY_NEG_FINISH (HMAC + encrypted session key) a hlásí Session key negotiate success.

Po poslání HEART_BEAT (cmd 9) se spojení ztrácí téměř okamžitě (Connection lost: None). To typicky indikuje, že zařízení odmítlo následující šifrovanou zprávu (tj. ověření HMAC/tag u DP_QUERY/HEART_BEAT selhalo) — tedy HMAC/tag u následující zprávy není to, co zařízení očekává.

Nejpravděpodobnější vysvětlení (priorita)

Nesoulad v HMAC při step-2 — to znamená, že zařízení a klient nepočítají HMAC nad stejným vstupem nebo nepoužívají stejný key. I když session key byl nakonec nasazen (ECB encrypt), zařízení už si může dělat interní kontrolu integrity a považuje další zprávy za neplatné.

Formát, který zařízení HMACuje, se liší — možná zařízení HMACuje např. remote_nonce || local_nonce nebo header || remote_nonce nebo zahrnuje/nezahrnuje 4-bytový retcode, které ty při výpočtu vynecháváš (log: „Skipping 4-byte retcode from payload“ — možný zdroj chyby).

Klíč pro HMAC není ten, co používáš — možná by mělo být použito originální device_key pro tento HMAC (nebo naopak session key). Nebo je potřeba truncation/padding (16 vs 32 B).

Endianness / serializace polí (seq, lengths) — v logu se objevuje „waiting for seq. number -102“ — zjisti, zda seq používáš jako signed/unsigned při konstrukci AAD/HMAC; jinak se může změnit pořadí bytů v HMAC vstupu.

AAD / GCM tag mismatch — neuronalyzované AAD (log ukazuje AAD=000000006d060000000400000050 použitou při decryptu), možná jiná AAD se má použít při ověření odpovědí nebo při DP zprávách.

Co udělat okamžitě — checklist s prioritou

Zaloguj surová data těsně při dekódování a těsně před odesláním:

remote_payload_raw.hex() (celé 52B payload před trimem)

remote_nonce.hex() (co jsi z něj extrahoval)

rkey_hmac_from_device.hex() (co zařízení poslalo)

rkey_hmac_expected.hex() (co tvůj kód spočítal; už to částečně vidíme jako wanted)

what_you_send_payload.hex() (co posíláš v SESS_KEY_NEG_FINISH i co posíláš v HEART_BEAT/DP_QUERY)

self.local_key.hex() (prefix/suffix stačí; důležitá je délka)
To rychle ukáže, jestli je problém v klíči nebo v message.

Ověř, co přesně porovnáváš při HMAC verifikaci step-2:

Jaký message používáš pro HMAC? (remote_nonce, remote_nonce||local_nonce, entire payload bez prvních 4B retcode…)

Jaký key používáš? (originální device_key z configu nebo encrypted_session_key? a v jaké formě — surové bytes nebo ASCII hex?)

Jaký hash? (SHA256 nebo něco jiného)

Vyzkoušej tyto varianty manuálně (lokálně) — rychlý test:

HMAC(key=device_key as bytes, msg=remote_nonce)

HMAC(key=device_key, msg=remote_nonce+local_nonce)

HMAC(key=device_key, msg=payload_without_4byte_retcode)

HMAC(key=session_key, msg=ciphertext)
(Porovnej výsledky s tím, co zařízení posílá jako got=....)

Zkontroluj, jestli se někde nepoužívá hex-string místo raw bytes — častá chyba: místo b'\x12\x34' se HMACuje '1234' jako ASCII. Ve tvém logu device_key=377b4f5641... — ujisti se, že do HMAC jde b'\x37\x7b...', ne text '377b...'.

Zkontroluj 4-byte retcode — log říká „Skipping 4-byte retcode from payload“ — ale možná zařízení HMACuje i tu čtyřku. Zkus spočítat HMAC i s retcode.

Zkus drobný experiment:

Pokud step-2 HMAC mismatch → vypiš obě hodnoty a zkus odvodit vzorec (obsah, délka, první/poslední byty).

Po nasazení těchto změn pošli HEART_BEAT znova — pokud HEART_BEAT projde, session key a HMAC logika jsou ok a můžeš pokračovat.

Odkaz pro inspiraci !!
https://pypi.org/project/tinytuya/