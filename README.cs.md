<p align="center">
  <img src="img/logo.png" alt="LocalTuya 2.0" width="500">
</p>

<p align="center">
  <strong>LocalTuya 2.0 — Nová generace lokálního ovládání Tuya</strong><br>
  <sub>Spravuje <a href="https://bildassystem.cz">BildaSystem.cz</a></sub>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/Bildass/localtuya/releases"><img src="https://img.shields.io/github/v/release/Bildass/localtuya?style=for-the-badge&color=green" alt="Release"></a>
  <a href="https://github.com/Bildass/localtuya/stargazers"><img src="https://img.shields.io/github/stars/Bildass/localtuya?style=for-the-badge" alt="Stars"></a>
  <a href="https://github.com/Bildass/localtuya/blob/master/LICENSE"><img src="https://img.shields.io/github/license/Bildass/localtuya?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="#-proč-tento-fork">Proč tento fork?</a> •
  <a href="#-instalace">Instalace</a> •
  <a href="#-funkce">Funkce</a> •
  <a href="#-migrace">Migrace</a> •
  <a href="#-dokumentace">Dokumentace</a>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> | 🇨🇿 <strong>Čeština</strong>
</p>

---

## 🤔 Proč tento fork?

Původní [LocalTuya](https://github.com/rospogrigio/localtuya) je skvělá integrace, ale vývoj se zpomalil. **LocalTuya 2.0** pokračuje tam, kde původní skončil:

| Problém | Původní LocalTuya | LocalTuya 2.0 řešení |
|---------|-------------------|-------------------|
| 😤 **Změna IP/klíče zařízení** | Proklikávat VŠECHNY entity jednu po druhé | ✅ **Quick Edit** - jedno okno, hotovo za sekundy |
| 😤 **Editace jedné entity** | Musíš projít celé zařízení | ✅ **Entity List** - skok přímo na konkrétní entitu |
| 😤 **Získání local_keys** | Ruční kopírování z Tuya IoT | ✅ **Cloud Sync** - jedno kliknutí načte všechny klíče |
| 😤 **Chyby v HA 2025.x** | Breaking changes, pády | ✅ **Plně kompatibilní** a otestováno |
| 😤 **Nelze spustit obě verze** | Musíš si vybrat | ✅ **Paralelní instalace** - testuj bez rizika |

> **💡 Shrnutí:** Opravili jsme každodenní frustrace, které uživatelé LocalTuya znají až příliš dobře.

---

## ✨ Funkce

### 🚀 Quick Edit (v6.0)
Změň host, local_key nebo verzi protokolu **bez** překonfigurování všech entit:

```
Nastavení → Zařízení → LocalTuya 2.0 → Konfigurovat
→ Vyber zařízení → Quick edit (host, key, protocol)
→ Změň co potřebuješ → Hotovo!
```

### ☁️ Cloud Key Sync (v6.0)
Automaticky načti local_keys pro **všechna zařízení** jedním klikem:
- Konec ručního kopírování z Tuya IoT Platform
- Zobrazí které klíče se změnily
- Aktualizuje pouze změněné klíče

### 🔄 Paralelní instalace
Běží vedle původního LocalTuya:
- Jiná doména (`localtuya_bildass`)
- Testuj před migrací
- Žádné konflikty

### 🛠️ Vylepšené Cloud API
- **Async aiohttp** místo blokujících requests
- **Token caching** - méně API volání
- **Paginace** - podpora 100+ zařízení
- **HMAC-SHA256** se správným nonce

---

## 📦 Instalace

### HACS (Doporučeno)

1. Otevři HACS → **Integrations**
2. Klikni **⋮** (tři tečky) → **Custom repositories**
3. Přidej: `https://github.com/Bildass/localtuya`
4. Kategorie: **Integration**
5. Najdi **LocalTuya 2.0** a klikni **Download**
6. **Restartuj Home Assistant**

### Manuální instalace

```bash
cd /config/custom_components
git clone https://github.com/Bildass/localtuya.git temp_localtuya
mv temp_localtuya/custom_components/localtuya_bildass .
rm -rf temp_localtuya
# Restartuj Home Assistant
```

---

## 🔄 Migrace

### Z původního LocalTuya

**Dobrá zpráva:** Můžeš spustit obě verze současně!

1. **Nainstaluj LocalTuya 2.0** přes HACS (zatím neodstraňuj původní)
2. **Přidej integraci:** Nastavení → Zařízení a služby → Přidat → **LocalTuya 2.0**
3. **Nakonfiguruj Cloud API** (volitelné, ale doporučené)
4. **Znovu přidej zařízení** - s Cloud Sync je to rychlé!
5. **Otestuj že vše funguje**
6. **Odstraň původní LocalTuya** až budeš spokojený

### Entity se změní

| Původní | LocalTuya 2.0 |
|---------|-------------|
| `switch.localtuya_xxx` | `switch.localtuya_bildass_xxx` |
| `light.localtuya_xxx` | `light.localtuya_bildass_xxx` |

**Tip:** Po migraci aktualizuj automatizace, skripty a dashboardy.

---

## 📖 Dokumentace

### Úvodní nastavení

1. **Přidej integraci:** Nastavení → Zařízení a služby → Přidat integraci → **LocalTuya 2.0**

2. **Nakonfiguruj Cloud API** (doporučeno):
   - Získej přihlašovací údaje z [Tuya IoT Platform](https://iot.tuya.com)
   - **Region:** eu / us / cn / in
   - **Client ID:** Cloud → Development → Overview
   - **Client Secret:** Stejné místo
   - **User ID:** Z "Link Tuya App Account"

3. **Přidej zařízení:** Použij Cloud Sync nebo manuální konfiguraci

### Podporovaná zařízení

| Typ | Příklady |
|-----|----------|
| **Switches** | Chytré zásuvky, relé, prodlužovačky |
| **Lights** | Žárovky, LED pásky, stmívače |
| **Covers** | Rolety, žaluzie, závěsy, garážová vrata |
| **Fans** | Stropní ventilátory, čističky vzduchu |
| **Climate** | Termostaty, ovladače klimatizace, topení |
| **Vacuums** | Robotické vysavače |
| **Sensors** | Teplota, vlhkost, pohyb, dveře/okna |
| **Numbers** | Jas, rychlost, nastavení teploty |
| **Selects** | Režimy, presety |

**Podporované protokoly:** 3.1, 3.2, 3.3, 3.4

### Měření energie

Pro zařízení s měřením spotřeby:

```yaml
sensor:
  - platform: template
    sensors:
      chytra_zasuvka_napeti:
        friendly_name: "Chytrá zásuvka - Napětí"
        value_template: "{{ state_attr('switch.moje_zasuvka', 'voltage') }}"
        unit_of_measurement: 'V'
        device_class: voltage
      chytra_zasuvka_proud:
        friendly_name: "Chytrá zásuvka - Proud"
        value_template: "{{ state_attr('switch.moje_zasuvka', 'current') }}"
        unit_of_measurement: 'mA'
        device_class: current
      chytra_zasuvka_vykon:
        friendly_name: "Chytrá zásuvka - Výkon"
        value_template: "{{ state_attr('switch.moje_zasuvka', 'current_consumption') }}"
        unit_of_measurement: 'W'
        device_class: power
```

### Debugging

Přidej do `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.localtuya_bildass: debug
    custom_components.localtuya_bildass.pytuya: debug
```

Také zapni **"Enable debugging for this device"** v konfiguraci zařízení.

---

## 📋 Changelog

### v6.0.0 - Revoluce Config Flow
- ✨ **Quick Edit** - změna host/local_key/protocol bez entit
- ✨ **Entity List** - přímá editace jedné entity
- ✨ **Cloud Sync** - načtení všech local_keys jedním klikem
- ✨ **Device Actions Menu** - nové organizované submenu
- 🔧 **Async Cloud API** - aiohttp, token caching, paginace
- 🔧 **Bezpečnost** - HMAC-SHA256 se správným nonce

### v5.5.0
- 🗑️ Odstraněna nefunkční QR autentizace
- 🔧 Zjednodušený config flow

### v5.4.0
- ✨ Paralelní instalace vedle původního LocalTuya
- 🔧 Změna domény na `localtuya_bildass`

### v5.3.1
- 🐛 Opravy kompatibility s Home Assistant 2025.x

---

## 🆚 Srovnání s originálem

| Funkce | Původní LocalTuya | LocalTuya 2.0 |
|--------|:-----------------:|:-----------:|
| Quick Edit (změna IP/klíče) | ❌ | ✅ |
| Přímá editace entity | ❌ | ✅ |
| Sync klíčů jedním klikem | ❌ | ✅ |
| HA 2025.x kompatibilní | ⚠️ Problémy | ✅ |
| Paralelní instalace | ❌ | ✅ |
| Async cloud API | ❌ | ✅ |
| Podpora 100+ zařízení | ⚠️ Omezeno | ✅ |
| Aktivní vývoj | ⚠️ Pomalý | ✅ |

---

## 🤝 Přispívání

Příspěvky jsou vítány! Postup:

1. Forkni repozitář
2. Vytvoř feature branch (`git checkout -b feature/super-funkce`)
3. Commitni změny (`git commit -m 'Přidání super funkce'`)
4. Pushni branch (`git push origin feature/super-funkce`)
5. Otevři Pull Request

---

## 📞 Podpora a kontakt

- 🌐 **Web:** [bildassystem.cz](https://bildassystem.cz)
- 📧 **Email:** info@bildassystem.cz
- 🐛 **Problémy:** [GitHub Issues](https://github.com/Bildass/localtuya/issues)
- 💬 **Diskuze:** [GitHub Discussions](https://github.com/Bildass/localtuya/discussions)

---

## 🙏 Poděkování

Postaveno na skvělé práci:
- [rospogrigio/localtuya](https://github.com/rospogrigio/localtuya) - Původní projekt
- [NameLessJedi](https://github.com/NameLessJedi), [mileperhour](https://github.com/mileperhour), [TradeFace](https://github.com/TradeFace) - Základ kódu
- [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) - Implementace protokolu 3.4

---

<p align="center">
  <strong>LocalTuya 2.0</strong><br>
  © 2024-2025 <a href="https://bildassystem.cz">BildaSystem.cz</a><br>
  <sub>Fork projektu <a href="https://github.com/rospogrigio/localtuya">rospogrigio/localtuya</a> • Licence GPL-3.0</sub>
</p>
