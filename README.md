<p align="center">
    <img src="https://i.imgur.com/w2EFlUe.png" width="128px" height="128px" alt="Ikona bežca"/>
    <h1 align="center">Proboj Runner</h1>
	<p align="center">Process and communication management pre Proboj.</p>
</p>

## Čo to je?

Proboj Runner zjednodušuje<sup>[citation needed]</sup> fungovanie Proboja. Má na starosti menežovanie
procesov a komunikáciu medzi serverom, hráčmi a observerom.

## Ako nainštalovať?

Buď clone repo a `pipenv install`, alebo na sústredení odporúčam Proboj Runner distribuovať ako
binárku *(v pythone je to fuj, ale je to pre účastníkov najjednoduchšie)*.

Binárku si vyrobíš takto:

```
pipenv run pyinstaller main.py
pipenv run staticx dist/main dist/proboj_runner
```

## Životný cyklus Proboja

Komunikácia medzi serverom, runnerom a hráčmi prebieha cez `stdin` / `stdout`.
Navyše, `stderr` hráčov a servera je presmerovaný do `stderr` runnera, takže chyby sa zobrazujú
v logu servera.

*Pozn.: Komunikácia prebieha cez Pythonové pajpy. To znamená, že ak plánujete presúvať dáta rádovo
väčšie ako pár MB, môžu sa pajpy upchať.*

Proboj Runner používa dva súbory:
- `config.json` - príkazy, ktoré sa majú spustiť (hráči a server)
- `games.json` - popis hier - kto s kým, mapa...

Pred začiatkom hry Proboj Runner spustí všetky potrebné procesy - server a hráčov.
Server na `stdin` dostane konfiguráciu hry:

```
CONFIG
hrac1 hrac2 hrac3 ...
...
.
```

Prvý riadok je označenie príkazu (`CONFIG`), na druhom riadku sú medzerou oddelené mená hráčov,
ostatné riadky sa prečítajú z `args` parametra hry v `games.json`. Príkaz končí riadkom s `.`.

Odteraz je celý priebeh hry v rukách servera.

## Príkazy

Príkaz sa skladá z názvu, argumentov, niekoľkých (0+) riadkov payloadu a riadkom s bodkou.

```
PRIKAZ args
payload
.
```

### `END` - koniec hry

Runner pozabíja všetky procesy (vrátane servera), odpoveď na tento príkaz nie je.

```
END
.
```

### `TO OBSERVER` - posielanie dát observeru

Celý payload príkazu sa zapíše do observer súboru.

```
TO OBSERVER
data
.
```

Odpoveď runnera:

```
OK
```

### `SCORES` - uloženie finálneho skóre

Payload sa skladá z jedného riadku pre každého hráča. Na každom z týchto riadkov je medzerou oddelené
meno hráča a jeho skóre. Tento príkaz sa momentálne dá vykonať len raz za hru.

```
SCORES
hrac 10
.
```

Odpoveď runnera:

```
OK
```

### `TO PLAYER hrac` - poslanie dát hráčovi

Celý payload príkazu sa pošle hráčovi na `stdin`.

```
TO PLAYER hrac
data
.
```

Odpoveď runnera:

```
OK
```

alebo, ak hráčov proces skončil:

```
DIED
```

### `READ PLAYER hrac` - čítanie dát z hráča

Prečíta sa celý `stdout` hráča až po prvý riadok s bodkou. Ak hráč nevyprodukuje koniec
výstupu (teda riadok s bodkou) do `timeout`-u zadefinovaného v `config.json`, runner ho zabije.

```
READ PLAYER hrac
.
```

Odpoveď runnera:

```
OK
data
.
```

alebo, ak hráčov proces skončil / vytimeoutoval:

```
DIED
```

### `KILL PLAYER hrac` - ukončenie procesu hráča

Zabije proces hráča.

```
KILL PLAYER hrac
.
```

Odpoveď runnera:

```
OK
```
