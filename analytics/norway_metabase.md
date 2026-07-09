# Norway App Store — Metabase Dashboard Setup

Настройка чартов в Metabase для каждого запроса из `norway_queries.md`.

---

## Запрос 1 — Топ-чарт

**Chart type:** `Table`

| Настройка | Значение |
|-----------|----------|
| Columns | position, app_name, developer_name, genre, rating, price |
| Sort | position → ASC |
| Column width | position — узкая, app_name — широкая |
| Conditional formatting | position 1–3 → зелёный фон |

**Dashboard filter:** добавь `feed_type` как фильтр с вариантами `free` / `paid`, привяжи к полю `feed_type` этой карточки.

---

## Запрос 2 — Тренд позиций

**Chart type:** `Line`

### Data tab

| Настройка | Значение |
|-----------|----------|
| X axis | `Snapshot Date` |
| Break out by (серии) | `App Name` |
| Y axis | `Position` |
| Per series → dots | включи для каждой серии через `...` → "Show dots" |

### Display tab

| Настройка | Значение |
|-----------|----------|
| Stack series | OFF |
| Show values on data points | OFF (иначе 300 цифр на графике) |
| Trend line | по желанию |

### Axes tab

| Настройка | Значение |
|-----------|----------|
| Y-axis → Rename | `Rank (10 = #1)` |
| Y-axis → Auto y-axis range | OFF |
| Y-axis → Min | `0` |
| Y-axis → Max | `11` |
| Y-axis → Scale | Linear |
| X-axis → Scale | Timeseries |

> **Почему ось от 0 до 11:** SQL возвращает значения `(11 - position)` — #1 место = 10, #10 место = 1. Линия идёт вверх = приложение растёт. "Invert axis" в Metabase не существует, поэтому инверсия сделана в запросе.

**Почему запрос не спагетти:** `consistent_apps` CTE отбирает только 10 приложений которые провели больше всего дней в топ-10 — в Metabase придёт максимум 10 линий.

**Dashboard filter:** `feed_type` — Text, одно значение, default `free`.

---

## Запрос 3 — Растущие приложения

**Chart type:** `Row` (горизонтальный bar)

| Настройка | Значение |
|-----------|----------|
| X axis | `avg_daily_delta` |
| Y axis | `app_name` |
| Series | `feed_type` (два цвета: free / paid) |
| Sort | По значению DESC |
| Colors | free → синий, paid → оранжевый |

> Самая "продажная" карточка — видно кто резко вырос за месяц.

---

## Запрос 4 — Жанровый breakdown (текущий)

Две карточки из одного запроса:

**Карточка A — `Pie`**

| Настройка | Значение |
|-----------|----------|
| Dimension | `genre` |
| Metric | `pct_of_chart` |
| Show legend | ✓ |

**Карточка B — `Bar`**

| Настройка | Значение |
|-----------|----------|
| X | `genre` |
| Y | `avg_rating`, `app_count` (два ряда) |
| Sort | `app_count` DESC |

**Dashboard filter:** `feed_type` привязать к обеим карточкам.

---

## Запрос 5 — Тренд жанров за 30 дней

**Chart type:** `Area` (stacked)

| Настройка | Значение |
|-----------|----------|
| X axis | `snapshot_date` |
| Y axis | `pct_of_chart` |
| Series | `genre` |
| Stacking | Stack ✓ |
| Y axis label | `% of chart` |

> Visualization → Display → Stacking → Stack

**Dashboard filter:** `feed_type`.

---

## Запрос 6 — Доминирование разработчиков

**Chart type:** `Row` (горизонтальный bar)

| Настройка | Значение |
|-----------|----------|
| X axis | `apps_in_chart` |
| Y axis | `developer_name` |
| Sort | `apps_in_chart` DESC |
| Tooltip columns | включи `apps`, `avg_position`, `avg_rating` |
| Column `apps` | скрыть из основного вида, оставить только в tooltip |

---

## Структура дашборда

```
┌─────────────────────┬──────────────────────┐
│  Топ-чарт Free      │  Топ-чарт Paid       │
│  (Table)            │  (Table)             │
├─────────────────────┴──────────────────────┤
│  Тренд позиций топ-20 (Line)               │
├─────────────────────┬──────────────────────┤
│  Жанры — Pie        │  Растущие (Row bar)  │
├─────────────────────┴──────────────────────┤
│  Тренд жанров (Stacked area)               │
├────────────────────────────────────────────┤
│  Разработчики (Row bar)                    │
└────────────────────────────────────────────┘
```

---

## Глобальные фильтры дашборда

| Фильтр | Тип | Привязать к картам | По умолчанию |
|--------|-----|--------------------|--------------|
| `feed_type` | Text — одно значение | Все карточки | `free` |
| `snapshot_date` | Date range | Запросы 2, 5 | последние 30 дней |
