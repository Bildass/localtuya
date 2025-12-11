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

- **v7.1.0** - Smart sync (ověřuje klíče před přepsáním)
- **v7.0.0** - Kompletní pytuya rewrite
- **v6.3.3** - Rollback (stabilní záloha)
