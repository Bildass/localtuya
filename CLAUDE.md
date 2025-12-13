# LocalTuya BildaSystem - Claude Instructions

## Verzování (POVINNÉ!)

**Semantic Versioning s BildaSystem konvencí:**

```
v7.x.y

x = MINOR - nové funkce, finální verze
y = PATCH - opravy, bugfixy
```

### Pravidla:

1. **Opravy/bugfixy:** Zvyšuj PATCH verzi
   - `v7.1.0` → `v7.1.1` → `v7.1.2` → `v7.1.3`
   - Pro každý bugfix, hotfix, drobnou opravu

2. **Nové funkce (finálky):** Zvyšuj MINOR verzi
   - `v7.1.x` → `v7.2.0` → `v7.3.0`
   - Pro novou funkcionalitu, která je funkční a otestovaná

3. **Breaking changes:** Zvyšuj MAJOR verzi
   - `v7.x.x` → `v8.0.0`
   - Pouze pro zásadní přepisy/nekompatibilní změny

### Git workflow (VŽDY dodržovat!):

1. **Aktualizovat verzi ve DVOU souborech:**
   - `const.py` → `VERSION = "X.Y.Z"`
   - `manifest.json` → `"version": "X.Y.Z"` (HACS čte tuto!)
2. `git add -A`
3. `git commit -m "vX.Y.Z: Popis změny"`
4. `git push origin master`
5. `git tag -a vX.Y.Z -m "vX.Y.Z: Popis"`
6. `git push origin vX.Y.Z`
7. **Vytvořit GitHub Release (HACS to vyžaduje!):**
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z: Popis" --notes "Changelog..."
   ```

**NIKDY nekopírovat soubory ručně! Vždy přes git tag/release.**

## Projekt

- **Repo:** https://github.com/Bildass/localtuya
- **Integrace:** `custom_components/localtuya_bildass`
- **HACS:** Custom repository

## Klíčové soubory

- `const.py` - VERSION konstanta (VŽDY aktualizovat!)
- `cloud_api.py` - Tuya Cloud API, sync local keys
- `config_flow.py` - UI konfigurace
- `common.py` - TuyaDevice, entity base
- `pytuya/` - Komunikace se zařízeními

## Aktuální verze

- **v7.3.16** - Add Smart Mini Bulb template, fix product_id detection in config_flow
- **v7.3.15** - Add rate limiting for Protocol 3.5 devices (0.5s min interval)
- **v7.3.9** - Fix CMD_STATUS routing (don't capture in seqno fallback, let it go to status_callback)
- **v7.3.8** - Broader seqno fallback (fuzzy seqno matching ±2)
- **v7.3.7** - Fix Protocol 3.5 seqno=0 response routing, data_received exception handling
- **v7.3.6** - Fix Protocol 3.5 status update exception handling (prevents connection drop)
- **v7.3.5** - Fix Protocol 3.5 CONTROL response handling
- **v7.3.4** - Heartbeat retry logic (3 failures before disconnect)
- **v7.3.3** - Fix Protocol 3.5 DP_QUERY (empty payload jak TinyTuya)
- **v7.3.2** - Nedis Pet Feeder template (Issue #1)
- **v7.3.1** - Fix Protocol 3.5 heartbeat JSON decode (Issue #2)
- **v7.1.0** - Smart sync (ověřuje klíče před přepsáním)
- **v7.0.0** - Kompletní pytuya rewrite
