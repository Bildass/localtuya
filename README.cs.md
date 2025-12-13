<p align="center">
  <img src="img/logo.png" alt="LocalTuya 2.0" width="500">
</p>

<p align="center">
  <strong>LocalTuya 2.0 — Nová generace lokálního ovládání Tuya zařízení</strong><br>
  <sub>Spravuje <a href="https://bildassystem.cz">BildaSystem.cz</a></sub>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/Bildass/localtuya/releases"><img src="https://img.shields.io/github/v/release/Bildass/localtuya?style=for-the-badge&color=green" alt="Release"></a>
  <a href="https://github.com/Bildass/localtuya/stargazers"><img src="https://img.shields.io/github/stars/Bildass/localtuya?style=for-the-badge" alt="Stars"></a>
  <a href="https://github.com/Bildass/localtuya/blob/master/LICENSE"><img src="https://img.shields.io/github/license/Bildass/localtuya?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="#-proč-localtuya-20">Proč?</a> •
  <a href="#-funkce">Funkce</a> •
  <a href="#-instalace">Instalace</a> •
  <a href="#️-plány-do-budoucna">Plány</a> •
  <a href="#-dokumentace">Dokumentace</a>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> | 🇨🇿 <strong>Čeština</strong>
</p>

---

## 🤔 Proč LocalTuya 2.0?

Původní [LocalTuya](https://github.com/rospogrigio/localtuya) byl skvělý projekt pro majitele Tuya zařízení. Jenže vývoj se zastavil, chyby se hromadily a Home Assistant se stále vyvíjel. **Rozhodli jsme se LocalTuya zachránit.**

### Problém

| Bolest | Co se dělo |
|--------|------------|
| 🐛 **HA 2024/2025 změny** | Pády, deprecation varování, nefunkční konfigurace |
| 🔧 **Protocol 3.5 zařízení** | Nepodporováno, novější zařízení nefungovala |
| 😤 **Změna IP/klíče** | Proklikávat VŠECHNY entity jednu po druhé |
| 📦 **Žádné šablony** | Konfigurovat 15 DP ručně pro každou žárovku |
| 🔐 **Složité nastavení cloudu** | Nutný developer účet, API klíče, atd. |

### Naše řešení

**LocalTuya 2.0** tohle všechno řeší. Jsme odhodlaní udržet lokální ovládání Tuya zařízení **živé a funkční**.

> 💡 **Filozofie:** Váš chytrý domov by měl fungovat **lokálně**, bez závislosti na cloudu. Proto LocalTuya existuje a proto ho udržujeme.

---

## ✨ Funkce

### 🆕 Podpora Protocol 3.5 (v7.0+)
Plná podpora nejnovějšího Tuya protokolu:
- **GCM šifrování** pro bezpečnou komunikaci
- **6699 packet prefix** handling
- **Správný heartbeat** s retry logikou
- Funguje s nejnovějšími Tuya zařízeními

### 📚 Knihovna zařízení (v7.0+)
Předkonfigurované šablony pro běžná zařízení:
- **Auto-detekce** podle product_id
- **Nastavení jedním klikem** - žádná ruční konfigurace DP
- **Komunitní šablony** - rostoucí knihovna

Aktuálně podporováno:
- Smart Mini Bulb RGB+CCT (Protocol 3.5)
- Smart Star Projector
- Tesla Air Purifier Mini
- Tesla Dehumidifier XL
- Tesla Power Strip PS300
- BlitzWolf Air Cleaner
- Nedis Pet Feeder
- KWS-302WF Energy Meter
- Circuit Breaker 63A
- Roleta M313EIRWT
- *...a další přibývají!*

### 🚀 Rychlá úprava
Změňte host, local_key nebo protokol **bez** překonfigurování entit:
```
Nastavení → Zařízení → LocalTuya 2.0 → Konfigurovat
→ Vybrat zařízení → Rychlá úprava
→ Hotovo za 10 sekund!
```

### ☁️ Cloud Sync klíčů
Stáhněte všechny local_keys **jedním klikem**:
- Žádné ruční kopírování z Tuya IoT
- Zobrazí které klíče se změnily
- Chytrá synchronizace - aktualizuje jen změněné

### 🔄 Paralelní instalace
Běží vedle původního LocalTuya:
- Jiná doména (`localtuya_bildass`)
- Testujte před migrací
- Žádné konflikty

### 🌍 Všechny Tuya regiony (v7.3.19+)
- EU - Střední Evropa
- EU West - Západní Evropa
- US - Západní Amerika
- US East - Východní Amerika
- CN - Čína
- IN - Indie
- **SG - Singapur** (nové!)

---

## 📦 Instalace

### HACS (Doporučeno)

1. Otevřete HACS → **Integrace**
2. Klikněte **⋮** → **Vlastní repozitáře**
3. Přidejte: `https://github.com/Bildass/localtuya`
4. Kategorie: **Integrace**
5. Najděte **LocalTuya 2.0** → **Stáhnout**
6. **Restartujte Home Assistant**

### Ruční instalace

```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git temp
mv temp/custom_components/localtuya_bildass .
rm -rf temp
# Restartujte Home Assistant
```

---

## 🗺️ Plány do budoucna

Aktivně vyvíjíme LocalTuya 2.0. Co chystáme:

### 🔜 Brzy

| Funkce | Status | Popis |
|--------|--------|-------|
| **QR Code přihlášení** | 🔬 Výzkum hotov | Přihlášení přes Tuya aplikaci - bez developer účtu! |
| **Water Heater platforma** | 📋 Plánováno | Podpora chytrých konvic, ohřívačů |
| **Více šablon zařízení** | 🔄 Průběžně | Komunitou přidávané konfigurace |

### ✅ Nedávno přidáno

| Verze | Funkce |
|-------|--------|
| v7.3.20 | Oprava zobrazení názvu šablony |
| v7.3.19 | Přidán Singapur + popisné názvy regionů |
| v7.3.18 | Optimalizace heartbeatu + optimistické UI |
| v7.3.16 | Smart Mini Bulb šablona + detekce product_id |
| v7.0.0 | Kompletní přepis pytuya + Protocol 3.5 |

### 💡 Nápady do budoucna

- **Matter bridge** - vystavit LocalTuya zařízení do Matter
- **Diagnostika zařízení** - vestavěný síťový analyzátor
- **Detekce firmware verze** - sledování aktualizací
- **Podpora scén** - aktivace Tuya scén

> 📣 **Máte nápad?** [Otevřete issue](https://github.com/Bildass/localtuya/issues) nebo [začněte diskuzi](https://github.com/Bildass/localtuya/discussions)!

---

## 📖 Dokumentace

### Rychlý start

1. **Nainstalujte** přes HACS (viz výše)
2. **Přidejte integraci:** Nastavení → Zařízení a služby → Přidat → **LocalTuya 2.0**
3. **Nastavte Cloud API** (volitelné, ale doporučené):
   - Získejte přihlašovací údaje z [Tuya IoT Platform](https://iot.tuya.com)
   - Region, Client ID, Client Secret, User ID
4. **Přidejte zařízení:** Cloud Sync automaticky vyplní údaje!

### Podporované platformy

| Platforma | Příklady |
|-----------|----------|
| **switch** | Chytré zásuvky, relé, prodlužovačky |
| **light** | Žárovky, LED pásky, stmívače |
| **cover** | Žaluzie, rolety, garážová vrata |
| **fan** | Stropní ventilátory, čističky vzduchu |
| **climate** | Termostaty, ovladače klimatizace |
| **vacuum** | Robotické vysavače |
| **sensor** | Teplota, vlhkost, spotřeba energie |
| **binary_sensor** | Pohyb, dveře/okna, únik vody |
| **number** | Jas, rychlost, nastavení teploty |
| **select** | Režimy, předvolby |

### Podporované protokoly

| Protokol | Šifrování | Status |
|----------|-----------|--------|
| 3.1 | AES-ECB | ✅ Podporováno |
| 3.2 | AES-ECB | ✅ Podporováno |
| 3.3 | AES-ECB | ✅ Podporováno |
| 3.4 | AES-GCM | ✅ Podporováno |
| **3.5** | AES-GCM | ✅ **Plná podpora** |

### Ladění

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

---

## 🔄 Migrace z původního LocalTuya

**Dobrá zpráva:** Můžete provozovat obě verze současně!

### Rychlé kroky

1. Nainstalujte LocalTuya 2.0 přes HACS
2. Exportujte stávající konfiguraci (local_keys jsou cenné!)
3. Přidejte zařízení do LocalTuya 2.0
4. Otestujte vše
5. Odstraňte původní až budete spokojeni

### Změna názvů entit

| Původní | LocalTuya 2.0 |
|---------|---------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Aktualizujte v:** Automatizacích, Skriptech, Dashboardech, Šablonách

> 📚 **Kompletní průvodce migrací:** Viz [Průvodce migrací](#průvodce-migrací) sekce níže.

---

## 📋 Historie verzí

### v7.3.x - Stabilita & UX
- **v7.3.20** - Oprava zobrazení názvu šablony v options flow
- **v7.3.19** - Přidány všechny Tuya regiony (SG, EU West, US East) s popisnými názvy
- **v7.3.18** - Optimalizace heartbeatu, optimistické UI aktualizace
- **v7.3.17** - Odstranění rate limitingu (způsoboval prodlevy)
- **v7.3.16** - Smart Mini Bulb šablona, oprava detekce product_id

### v7.0.x - Revoluce Protocol 3.5
- **v7.0.0** - Kompletní přepis pytuya, podpora Protocol 3.5, Knihovna zařízení

### v6.x - Přepracování Config Flow
- **v6.0.0** - Rychlá úprava, Seznam entit, Cloud Sync, Async API

<details>
<summary>📜 Starší verze...</summary>

### v5.x
- **v5.5.0** - Odstranění nefunkční QR auth, zjednodušení flow
- **v5.4.0** - Paralelní instalace, změna domény
- **v5.3.1** - Kompatibilita s HA 2025.x

</details>

---

## 🆚 Srovnání

| Funkce | Původní LocalTuya | LocalTuya 2.0 |
|--------|:-----------------:|:-------------:|
| Protocol 3.5 | ❌ | ✅ |
| Šablony zařízení | ❌ | ✅ |
| Rychlá úprava | ❌ | ✅ |
| Cloud Key Sync | ❌ | ✅ |
| HA 2024/2025 | ⚠️ Problémy | ✅ |
| Paralelní instalace | ❌ | ✅ |
| 100+ zařízení | ⚠️ Omezeno | ✅ |
| Aktivní vývoj | ❌ Zastaveno | ✅ **Aktivní** |

---

## 🤝 Přispívání

Vítáme příspěvky!

### Jak pomoci

- 🐛 **Hlášení chyb** - [Otevřete issue](https://github.com/Bildass/localtuya/issues)
- 💡 **Návrhy funkcí** - [Začněte diskuzi](https://github.com/Bildass/localtuya/discussions)
- 📚 **Přidejte šablony** - Sdílejte vaše funkční konfigurace
- 🌍 **Překlady** - Pomozte lokalizovat integraci
- 🔧 **Kód** - PR jsou vítány!

### Vývoj

```bash
git clone https://github.com/Bildass/localtuya.git
cd localtuya
# Vytvořte feature branch
git checkout -b feature/skvela-funkce
# Proveďte změny, commitněte, pushněte
git push origin feature/skvela-funkce
# Otevřete PR
```

---

## 📞 Podpora & Kontakt

- 🌐 **Web:** [bildassystem.cz](https://bildassystem.cz)
- 📧 **Email:** info@bildassystem.cz
- 🐛 **Issues:** [GitHub Issues](https://github.com/Bildass/localtuya/issues)
- 💬 **Diskuze:** [GitHub Discussions](https://github.com/Bildass/localtuya/discussions)

---

## 🙏 Poděkování

Postaveno na skvělé práci:
- [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) - Původní projekt
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - Implementace protokolu
- [make-all/tuya-local](https://github.com/make-all/tuya-local) - Inspirace pro QR auth výzkum

**Komunitní přispěvatelé:**
- Všichni, kdo hlásí chyby, navrhují funkce a sdílí konfigurace zařízení!

---

<p align="center">
  <strong>LocalTuya 2.0</strong><br>
  Udržujeme lokální ovládání Tuya <strong>naživu</strong>.<br><br>
  © 2024-2025 <a href="https://bildassystem.cz">BildaSystem.cz</a><br>
  <sub>Fork projektu <a href="https://github.com/rospogrigio/localtuya">rospogrigio/localtuya</a> • Licence GPL-3.0</sub>
</p>

---

<details>
<summary><h2>📚 Kompletní průvodce migrací</h2></summary>

### Z původního LocalTuya

**Dobrá zpráva:** Můžete provozovat obě verze současně! A **nemusíte znovu získávat local_keys** - už jsou ve vaší konfiguraci!

#### Rychlý přehled

1. **Nainstalujte LocalTuya 2.0** přes HACS (původní zatím neodstraňujte)
2. **Exportujte stávající data zařízení** (viz níže)
3. **Přidejte integraci:** Nastavení → Zařízení a služby → Přidat → **LocalTuya 2.0**
4. **Znovu přidejte zařízení** pomocí exportovaných dat (Cloud API není potřeba!)
5. **Otestujte že vše funguje**
6. **Odstraňte původní LocalTuya** až budete spokojeni

---

### 📋 Krok 1: Export stávající konfigurace

Vaše stávající konfigurace zařízení (včetně cenných `local_key` hodnot) jsou uloženy v Home Assistant úložišti.

#### Možnost A: Python skript (Doporučeno pro 10+ zařízení)

Vytvořte `export_localtuya.py` v `/config`:

```python
#!/usr/bin/env python3
"""Export LocalTuya konfigurace pro migraci do LocalTuya 2.0"""

import json
from pathlib import Path

config_path = Path('/config/.storage/core.config_entries')
with open(config_path, 'r') as f:
    data = json.load(f)

devices = []
for entry in data['data']['entries']:
    if entry.get('domain', '').lower() == 'localtuya':
        device_data = entry.get('data', {})
        devices.append({
            'name': entry.get('title', 'Neznámé'),
            'device_id': device_data.get('device_id'),
            'local_key': device_data.get('local_key'),
            'host': device_data.get('host'),
            'protocol_version': device_data.get('protocol_version', '3.3'),
            'entities': device_data.get('entities', [])
        })

output_path = Path('/config/localtuya_export.json')
with open(output_path, 'w') as f:
    json.dump(devices, f, indent=2, ensure_ascii=False)

print(f"✅ Exportováno {len(devices)} zařízení do {output_path}")
```

Spusťte přes SSH: `python3 /config/export_localtuya.py`

#### Možnost B: Ruční (Málo zařízení)

1. Otevřete `/config/.storage/core.config_entries`
2. Hledejte `"domain": "localtuya"`
3. Zkopírujte relevantní záznamy

---

### 📝 Krok 2: Přidání zařízení do LocalTuya 2.0

Pro každé zařízení:

1. **Nastavení → Zařízení a služby → LocalTuya 2.0 → Konfigurovat**
2. **Přidat nové zařízení**
3. Zadejte údaje z exportu: Device ID, Host, Local Key, Protokol
4. Nakonfigurujte entity pomocí DP čísel z exportu
5. Opakujte

> ⏱️ ~2-3 minuty na zařízení s připravenými daty

---

### ⚠️ Změna názvů entit

Vaše entity ID se změní:

| Původní | LocalTuya 2.0 |
|---------|---------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Aktualizujte v:** Automatizacích, Skriptech, Dashboardech, Šablonách, Skupinách

---

### 💡 Tipy

- **Nastavte statické IP** pro Tuya zařízení v routeru
- **Uchovejte export soubor** jako zálohu
- **Migrujte po dávkách** pokud máte hodně zařízení
- **Testujte každou dávku** než budete pokračovat

</details>

---

<details>
<summary><h2>⚡ Nastavení měření energie</h2></summary>

Pro zařízení s měřením spotřeby (chytré zásuvky, prodlužovačky):

```yaml
# configuration.yaml
sensor:
  - platform: template
    sensors:
      chytra_zasuvka_napeti:
        friendly_name: "Chytrá zásuvka - Napětí"
        value_template: "{{ state_attr('switch.localtuya_bildass_zasuvka', 'voltage') }}"
        unit_of_measurement: 'V'
        device_class: voltage

      chytra_zasuvka_proud:
        friendly_name: "Chytrá zásuvka - Proud"
        value_template: "{{ state_attr('switch.localtuya_bildass_zasuvka', 'current') }}"
        unit_of_measurement: 'mA'
        device_class: current

      chytra_zasuvka_vykon:
        friendly_name: "Chytrá zásuvka - Výkon"
        value_template: "{{ state_attr('switch.localtuya_bildass_zasuvka', 'current_consumption') }}"
        unit_of_measurement: 'W'
        device_class: power
```

</details>
