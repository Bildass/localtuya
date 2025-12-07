# LocalTuya BildaSystem

[🇬🇧 English](README.md) | 🇨🇿 **Čeština**

> **Aktivně vyvíjený fork od [BildaSystem.cz](https://bildassystem.cz)**

Fork integrace [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) s vylepšeným config flow, automatickým načítáním klíčů z cloudu a kompatibilitou s Home Assistant 2025.x.

---

## Hlavní výhody oproti původnímu LocalTuya

| Funkce | Původní | BildaSystem |
|--------|---------|-------------|
| Quick Edit (změna IP/klíče) | Proklikávání všech entit | Jedno okno, hotovo |
| Editace entity | Musíš projít všechny | Vybereš jednu konkrétní |
| Sync klíčů z cloudu | Ruční kopírování | Jedno kliknutí |
| HA 2025.x kompatibilita | Chyby | Funguje |
| Paralelní instalace | Ne | Ano (jiný domain) |

---

## Instalace

### HACS (doporučeno)
1. HACS → Integrations → Custom repositories
2. Přidej `https://github.com/Bildass/localtuya`
3. Nainstaluj "LocalTuya BildaSystem"
4. Restartuj Home Assistant

### Manuální instalace
```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git
mv localtuya/custom_components/localtuya_bildass .
rm -rf localtuya
```

---

## Konfigurace

### 1. Přidání integrace
Settings → Devices & Services → Add Integration → **LocalTuya BildaSystem**

### 2. Cloud API (doporučeno)
Zadej přihlašovací údaje z [Tuya IoT Platform](https://iot.tuya.com):
- **Region** - eu/us/cn/in
- **Client ID** - z Cloud → Development → Overview
- **Client Secret** - tamtéž
- **User ID** - z Link Tuya App Account

> Bez Cloud API musíš local_key zadávat ručně.

### 3. Hlavní menu
Po konfiguraci uvidíš:
- **Add a new device** - přidat zařízení
- **Edit a device** - upravit existující
- **Sync local keys from cloud** - načíst klíče z cloudu
- **Reconfigure Cloud API** - změnit cloud credentials

### 4. Quick Edit (NOVINKA v6.0)
Při editaci zařízení:
1. Vyber zařízení
2. Zvol **Quick edit (host, key, protocol)**
3. Změň co potřebuješ
4. Hotovo - bez proklikávání entit!

### 5. Sync from Cloud (NOVINKA v6.0)
Automaticky načte local_keys pro všechna zařízení:
1. Hlavní menu → **Sync local keys from cloud**
2. Zobrazí se které klíče se změnily
3. Potvrď → klíče se aktualizují

---

## Podporovaná zařízení

- Switches (vypínače)
- Lights (světla)
- Covers (rolety, žaluzie)
- Fans (ventilátory)
- Climates (termostaty, klimatizace)
- Vacuums (vysavače)
- Sensors (čidla)
- Numbers (číselné hodnoty)
- Selects (výběry)

**Protokoly:** 3.1, 3.2, 3.3, 3.4

---

## Energy Monitoring

Pro zařízení s měřením spotřeby můžeš vytvořit template sensory:

```yaml
sensor:
  - platform: template
    sensors:
      tuya_voltage:
        value_template: "{{ states.switch.my_switch.attributes.voltage }}"
        unit_of_measurement: 'V'
      tuya_current:
        value_template: "{{ states.switch.my_switch.attributes.current }}"
        unit_of_measurement: 'mA'
      tuya_power:
        value_template: "{{ states.switch.my_switch.attributes.current_consumption }}"
        unit_of_measurement: 'W'
```

---

## Debugging

Přidej do `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

Pak v editaci zařízení zaškrtni **Enable debugging for this device**.

---

## Changelog

### v6.0.0 (Current)
- **Major Config Flow Overhaul**
  - Quick Edit - změna host/local_key/protocol bez entit
  - Entity List - přímá editace jedné entity
  - Sync from Cloud - načtení klíčů jedním klikem
  - Device Actions Menu - nové submenu
- **Enhanced Cloud API**
  - Async aiohttp místo requests
  - Token caching
  - Paginace pro 100+ zařízení
  - HMAC-SHA256 s nonce

### v5.5.0
- Odstranění nefunkční QR autentizace
- Zjednodušený config flow

### v5.4.0
- Paralelní instalace vedle původního LocalTuya
- Změna domain na `localtuya_bildass`

### v5.3.1
- Opravy kompatibility s HA 2025.x

---

## Kontakt

- Web: [bildassystem.cz](https://bildassystem.cz)
- Email: info@bildassystem.cz
- GitHub: [Bildass/localtuya](https://github.com/Bildass/localtuya)
- Issues: [GitHub Issues](https://github.com/Bildass/localtuya/issues)

---

## Development

### Vydání nové verze (Release Workflow)

HACS používá Git tagy pro zobrazení verzí. Bez tagů ukazuje commit hashe.

```bash
cd /home/core/projects/localtuya

# 1. Uprav verzi v manifest.json
#    custom_components/localtuya_bildass/manifest.json
#    "version": "6.1.0"

# 2. Commitni změny
git add .
git commit -m "v6.1.0: Popis změn"

# 3. Vytvoř tag (musí odpovídat verzi v manifestu)
git tag v6.1.0 -m "v6.1.0: Popis změn"

# 4. Pushni vše
git push origin master
git push origin v6.1.0
```

**Volitelně:** Na GitHub vytvoř Release z tagu pro hezčí release notes.

---

## Credits

Založeno na práci:
- [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) - původní projekt
- [NameLessJedi](https://github.com/NameLessJedi), [mileperhour](https://github.com/mileperhour), [TradeFace](https://github.com/TradeFace) - základ kódu
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - protokol 3.4

---

*LocalTuya BildaSystem © 2024-2025 [BildaSystem.cz](https://bildassystem.cz) | Fork of [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) (GPL-3.0)*
