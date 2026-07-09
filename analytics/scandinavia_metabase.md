# Scandinavia App Store — Metabase Dashboard Setup

Настройка дашборда для разового пакета Скандинавия (NO, SE, DK, FI).
Продукт: срез за 30 дней, продаётся один раз как data report.

---

## Структура дашборда

```
┌──────────────────────────────────────────────────┐
│  HEADER: Scandinavia App Store Intelligence      │
│  Period: <date range> · Free & Paid              │
├────────────┬────────────┬────────────┬───────────┤
│  NO Top 10 │  SE Top 10 │  DK Top 10 │  FI Top10 │
│  (Table)   │  (Table)   │  (Table)   │  (Table)  │
├────────────┴────────────┴────────────┴───────────┤
│  Cross-country hits — топ по всему региону       │
│  (Table с badge: сколько стран)                  │
├──────────────────────────┬───────────────────────┤
│  Жанры по странам        │  Растущие приложения  │
│  (Grouped bar)           │  (Row bar)            │
├──────────────────────────┴───────────────────────┤
│  Тренд жанров по региону (Stacked area)          │
├──────────────────────────┬───────────────────────┤
│  Доминирование           │  Локальные хиты       │
│  разработчиков (Row bar) │  (Table)              │
└──────────────────────────┴───────────────────────┘
```

**Глобальные фильтры дашборда:**
- `feed_type` — Text, одно значение (`free` / `paid`), привязать ко всем картам
- `country` — Text, multi-select (`NO`, `SE`, `DK`, `FI`)
- `snapshot_date` — Date range, привязать к картам с историей (запросы 6, 7)

---

## Запрос 1 — Топ-чарт по каждой стране

Четыре отдельные карточки — по одной на каждую страну. Один и тот же запрос, фильтр по `country`.

**Chart type:** `Table`

| Настройка | Значение |
|-----------|----------|
| Columns | position, app_name, developer_name, genre, rating |
| Sort | position → ASC |
| Row limit | 10 (для компактного вида) |
| Conditional formatting | position 1 → золотой, 2–3 → серебро |
| Card title | `🇳🇴 Norway — Top 10 Free` (менять под страну и тип) |

> Создай 4 карточки с фиксированным фильтром `country = NO / SE / DK / FI`. Разместить в одну строку.

---

## Запрос 2 — Сравнение топ-10 рядом

**Chart type:** `Table`

| Настройка | Значение |
|-----------|----------|
| Columns | country, position, app_name, developer_name, genre, rating |
| Sort | position ASC, country ASC |
| Group rows by | `country` (если поддерживается в версии) |
| Conditional formatting | position 1 → зелёный |

---

## Запрос 3 — Cross-country hits

Ключевая карточка пакета — что работает по всему региону.

**Chart type:** `Table`

| Настройка | Значение |
|-----------|----------|
| Columns | app_name, developer_name, genre, countries_count, positions_by_country, avg_position |
| Sort | countries_count DESC, avg_position ASC |
| Conditional formatting | countries_count = 4 → зелёный, 3 → жёлтый, 2 → стандарт |
| Column `countries_count` | переименовать в `Countries` |
| Column `positions_by_country` | переименовать в `Positions` |

> Это главная карточка для покупателя — он видит что актуально по всей Скандинавии.

---

## Запрос 4 — Локальные хиты

**Chart type:** `Table`

| Настройка | Значение |
|-----------|----------|
| Columns | country, position, app_name, developer_name, genre |
| Sort | country ASC, position ASC |
| Filter | добавь dashboard filter `country` |
| Card title | `Local Hits — Only in One Country` |

---

## Запрос 5 — Жанровый breakdown по странам

**Chart type:** `Bar` (grouped, не stacked)

| Настройка | Значение |
|-----------|----------|
| X axis | `genre` |
| Y axis | `pct_of_chart` |
| Series / Group | `country` |
| Colors | NO → красный, SE → синий, DK → жёлтый, FI → белый/голубой |
| Sort | по суммарному значению DESC |
| Y axis label | `% of chart` |

> Visualization → Display → "Group bars" (не Stack).
> Видно культурные различия: Games доминируют в FI, Entertainment — в SE.

---

## Запрос 6 — Тренд жанров за 30 дней

Четыре отдельные карточки — по одной на страну. Или одна с фильтром `country`.

**Chart type:** `Area` (stacked)

| Настройка | Значение |
|-----------|----------|
| X axis | `snapshot_date` |
| Y axis | `pct_of_chart` |
| Series | `genre` |
| Stacking | Stack ✓ |
| Y axis label | `% of chart` |

> Visualization → Display → Stacking → Stack

---

## Запрос 7 — Растущие приложения по региону

**Chart type:** `Row` (горизонтальный bar)

| Настройка | Значение |
|-----------|----------|
| X axis | `avg_daily_delta` |
| Y axis | `app_name` |
| Series | `country` |
| Colors | NO → красный, SE → синий, DK → жёлтый, FI → голубой |
| Sort | по значению DESC |
| Tooltip | `best_position`, `max_days_in_top`, `days_rising` |

---

## Запрос 8 — Доминирование разработчиков

**Chart type:** `Row` (горизонтальный bar)

| Настройка | Значение |
|-----------|----------|
| X axis | `total_slots` |
| Y axis | `developer_name` |
| Color | `countries_present` (gradient: 1 → светлый, 4 → тёмный) |
| Sort | `countries_present` DESC, `total_slots` DESC |
| Tooltip | `unique_apps`, `avg_position`, `countries` |

---

## Как оформить для продажи (разовый пакет)

### Что экспортировать из Metabase

1. **PDF дашборда** — Metabase → Share → Export as PDF
2. **CSV файлы** — каждую карточку → Download → CSV

### Состав пакета для покупателя

```
scandinavia_app_store_<month>_<year>/
├── report.pdf                    ← экспорт дашборда из Metabase
├── data/
│   ├── top_chart.csv             ← запрос 1
│   ├── cross_country_hits.csv    ← запрос 3
│   ├── local_hits.csv            ← запрос 4
│   ├── genre_stats.csv           ← запрос 5
│   ├── rising_apps.csv           ← запрос 7
│   └── developers.csv            ← запрос 8
└── README.txt                    ← описание колонок и методологии
```

### README.txt — что писать

```
Scandinavia App Store Intelligence Report
Period: <start_date> — <end_date>
Countries: Norway (NO), Sweden (SE), Denmark (DK), Finland (FI)
Source: Apple App Store public RSS + iTunes Lookup API
Updated: daily snapshots, aggregated over 30 days

Files:
- top_chart.csv        Current top 200 apps per country (free & paid)
- cross_country.csv    Apps ranked in top 20 in 2+ countries
- local_hits.csv       Apps exclusive to one country (top 50)
- genre_stats.csv      Genre breakdown per country
- rising_apps.csv      Apps with highest avg daily rank improvement
- developers.csv       Publisher dominance across the region

Columns:
- position             Chart rank (1 = #1 in store)
- position_delta       Daily rank change (positive = improved)
- days_in_top          Consecutive days in chart
- pct_of_chart         % of all 200 chart slots occupied by genre
- countries_count      Number of Scandinavian markets app appears in
```

---

## Цена пакета

| Вариант | Цена |
|---------|------|
| PDF отчёт (только визуализация) | €250 |
| PDF + все CSV файлы | €450 |
| PDF + CSV + README (полный пакет) | €600 |
| Тот же пакет x4 страны отдельно (NO, SE, DK, FI) | €800 |
