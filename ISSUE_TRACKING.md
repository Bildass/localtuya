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

### Co bylo opraveno (v7.0.0) - KOMPLETNÍ PŘEPIS OD ZÁKLADU
**Datum: 2025-12-11**

**Kompletní nový pytuya modul** - ne refaktoring, ale od základu nový kód podle TinyTuya reference.

#### Nová modulární architektura:
```
pytuya/
├── __init__.py     # Public API + backward compat aliasy (269 řádků)
├── constants.py    # Všechny konstanty, commands, payloads (240 řádků)
├── cipher.py       # AES-ECB (v3.1-3.4) + AES-GCM (v3.5) (150 řádků)
├── message.py      # TuyaMessage, TuyaHeader, exceptions (90 řádků)
├── protocol.py     # pack/unpack pro 55AA i 6699 (380 řádků)
└── device.py       # TuyaProtocol, TuyaListener, connect() (750 řádků)
```

#### Podpora protokolů:
| Verze | Prefix | Šifrování | Checksum | Session Key |
|-------|--------|-----------|----------|-------------|
| 3.1 | 55AA | ECB | CRC32 | Ne |
| 3.2/3.3 | 55AA | ECB | CRC32 | Ne |
| 3.4 | 55AA | ECB | HMAC-SHA256 | Ano |
| 3.5 | 6699 | GCM | GCM Tag | Ano |

#### Klíčové implementace:

**Session Key Negotiation (device.py:525-585):**
```python
async def _negotiate_session_key(self):
    # Step 1: Send local_nonce
    response = await self._exchange_quick(CMD_SESS_KEY_NEG_START, self.local_nonce)

    # Step 2: Receive remote_nonce + HMAC(local_nonce)
    self.remote_nonce = payload[:16]

    # Calculate session key
    xor_result = bytes(a ^ b for a, b in zip(self.local_nonce, self.remote_nonce))

    if self.protocol_version >= 3.5:
        # Protocol 3.5: AES-GCM encrypt, take ciphertext only
        iv = self.local_nonce[:12]
        gcm_cipher = Cipher(algorithms.AES(self.device_key), modes.GCM(iv))
        encryptor = gcm_cipher.encryptor()
        encrypted = encryptor.update(xor_result) + encryptor.finalize()
        session_key = encrypted[:16]  # ONLY ciphertext, no IV/tag!
    else:
        # Protocol 3.4: AES-ECB encrypt
        session_key = cipher.encrypt_ecb(xor_result, pad=False)[:16]

    # Step 3: Send HMAC(remote_nonce)
    await self._exchange_quick(CMD_SESS_KEY_NEG_FINISH, hmac_remote)
```

**6699 Message Format (protocol.py:150-200):**
```python
# Structure: [header 18B][nonce 12B][encrypted_payload][tag 16B][suffix 4B]
# Header: prefix(4) + version(1) + reserved(1) + seqno(4) + cmd(4) + length(4)
# AAD = header bytes 4-18 (version through length)
# GCM encrypts payload, authenticates AAD
```

#### Lokální testy (všechny prošly):
- [x] Import všech modulů
- [x] TuyaProtocol má všechny metody (add_dps_to_request, status, set_dp, etc.)
- [x] TuyaListener interface kompletní
- [x] ContextualLogger pro common.py
- [x] AES-ECB encrypt/decrypt
- [x] AES-GCM encrypt/decrypt s AAD
- [x] 55AA message pack/unpack (v3.1, 3.3, 3.4)
- [x] 6699 message pack/unpack (v3.5)
- [x] Session key calculation algoritmus
- [x] Backward compat aliasy (PREFIX_VALUE, CONTROL, etc.)

#### GitHub Release:
- Tag: v7.0.0
- URL: https://github.com/Bildass/localtuya/releases/tag/v7.0.0
- HACS: Ready for update

#### Čeká na test:
- [ ] Test s reálným zařízením Protocol 3.3
- [ ] Test s Switch-Satna (Protocol 3.5)
- [ ] Ověření session key negotiation s reálným zařízením

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