# Ukraine App Store — Tableau Setup

Гайд по каждому чарту. Каждый чарт = новый Sheet (вкладка внизу экрана).

## Основные понятия Tableau
- **Синие таблетки** = Dimensions (категории: app_name, genre, feed_type)
- **Зелёные таблетки** = Measures (числа: position, rating, price)
- **Marks card** = управляет Color, Size, Label, Tooltip
- Правая кнопка на таблетке → **Dimension** чтобы убрать агрегацию

---

## Чарт 1 — Топ-чарт

**Data source:** `ukraine_top_chart.csv`
**Sheet name:** `UA | Top Chart | Apr 15 – May 15, 2026`

| Shelf | Поле |
|-------|------|
| Columns | `Feed Type` |
| Rows | `App Name` |
| Marks type | **Text** |
| Text (Marks) | `Position`, `Rating`, `Price` |
| Filter | `Feed Type` → выбери `free` |
| Sort | правая кнопка на `App Name` → Sort → By field → `Position` → Ascending |

**Style:**
- Format → Shading → чередующиеся строки
- Правая кнопка на `Position` в Text → Format → выдели минимальные значения зелёным

---

## Чарт 2 — Тренд позиций

**Data source:** `ukraine_trend.csv`
**Sheet name:** `UA | Position Trend | Apr 15 – May 15, 2026`

| Shelf | Поле | Как |
|-------|------|-----|
| Columns | `Snapshot Date` | правая кнопка → **Day** (нижний вариант, continuous — зелёный) |
| Rows | `Position` | правая кнопка → **Dimension** |
| Color (Marks) | `App Name` | перетащи |
| Marks type | **Line** | |
| Filter | `Feed Type` | выбери `free` |

**Style:**
- Правая кнопка на оси Y → **Edit axis** → Title: `Rank (10 = #1)` → Fixed: Min `0`, Max `11`
- Правая кнопка на оси Y → **Edit axis** → Scale → **Reversed** ✓ (тогда не нужна формула инверсии)
- Marks → **Label** → перетащи `App Name` → Show mark labels: End of line

> **Лайфхак:** в Tableau есть встроенный **Reversed axis** — правая кнопка на оси Y → Edit axis → Scale → Reversed. Тогда #1 наверху автоматически без SQL-формулы.

---

## Чарт 3 — Растущие приложения

**Data source:** `ukraine_rising.csv`
**Sheet name:** `UA | Rising Apps | Apr 15 – May 15, 2026`

| Shelf | Поле | Как |
|-------|------|-----|
| Columns | `Avg Daily Delta` | перетащи |
| Rows | `App Name` | перетащи |
| Color (Marks) | `Feed Type` | перетащи |
| Marks type | **Bar** | |
| Sort | правая кнопка на `App Name` → Sort → By field → `Avg Daily Delta` → Descending |
| Filter | `Feed Type` | выбери оба или один |

**Style:**
- Marks → **Label** → Show mark labels ✓ → перетащи `Avg Daily Delta` → Format: 1 decimal
- Color → Edit colors: `free` → синий `#4285F4`, `paid` → оранжевый `#FF6D00`
- Format → вертикальная ось → скрой линии сетки

---

## Чарт 4 — Жанровый breakdown

**Data source:** `ukraine_genre_snapshot.csv`
**Sheet name:** `UA | Genre Breakdown | May 15, 2026`

| Shelf | Поле | Как |
|-------|------|-----|
| Columns | *(пусто)* | |
| Rows | *(пусто)* | |
| Color (Marks) | `Genre` | перетащи |
| Angle (Marks) | `Pct Of Chart` | перетащи (появится после выбора Pie) |
| Marks type | **Pie** | |
| Filter | `Feed Type` | выбери `free` |
| Label (Marks) | `Genre` + `Pct Of Chart` | перетащи оба |

**Style:**
- Marks → Size → увеличь круг до максимума
- Label → Font 11px, Bold
- Format → `Pct Of Chart` → Number → Percentage, 1 decimal

---

## Чарт 5 — Тренд жанров

**Data source:** `ukraine_genre_trend.csv`
**Sheet name:** `UA | Genre Trend | Apr 15 – May 15, 2026`

| Shelf | Поле | Как |
|-------|------|-----|
| Columns | `Snapshot Date` | правая кнопка → **Day** (continuous — зелёный) |
| Rows | `Pct Of Chart` | SUM (оставь как есть) |
| Color (Marks) | `Genre` | перетащи |
| Marks type | **Area** | |
| Filter | `Feed Type` | выбери `free` |

**Style:**
- Analysis → Stack Marks → **On** (stacked area)
- Правая кнопка на оси Y → Edit axis → Title: `% of Chart`
- Правая кнопка на оси Y → Format → Numbers → Percentage

---

## Чарт 6 — Разработчики

**Data source:** `ukraine_developers.csv`
**Sheet name:** `UA | Developer Dominance | May 15, 2026`

| Shelf | Поле | Как |
|-------|------|-----|
| Columns | `Apps In Chart` | перетащи |
| Rows | `Developer Name` | перетащи |
| Color (Marks) | `Apps In Chart` | перетащи → Edit colors → gradient синий |
| Marks type | **Bar** | |
| Tooltip (Marks) | `Avg Position`, `Avg Rating`, `Apps` | перетащи все три |
| Sort | правая кнопка на `Developer Name` → Sort → By field → `Apps In Chart` → Descending |
| Filter | `Feed Type` | выбери `free` |

**Style:**
- Marks → **Label** → Show mark labels ✓ → перетащи `Apps In Chart`
- Format → скрой вертикальную линию сетки

---

## Дашборд — собираем всё вместе

1. Нажми иконку **New Dashboard** (внизу рядом с вкладками)
2. Размер: Device Preview → Desktop → 1400 x 900
3. Перетаскивай чарты с панели слева на холст:

```
┌─────────────────────────────────────────────┐
│  [Filter: Feed Type]  [Filter: Date Range]  │
├──────────────────────┬──────────────────────┤
│  Top Chart (Table)   │  Genre Breakdown(Pie)│
├──────────────────────┴──────────────────────┤
│  Position Trend (Line)                      │
├──────────────────────┬──────────────────────┤
│  Rising Apps (Bar)   │  Developers (Bar)    │
├──────────────────────┴──────────────────────┤
│  Genre Trend (Stacked area)                 │
└─────────────────────────────────────────────┘
```

4. Добавь глобальный фильтр:
   - Кликни на любой чарт → стрелочка вверху → **Use as filter**
   - Или: Dashboard → Actions → Add action → Filter

---

## Публикация

**File → Save to Tableau Public**
→ Даёт публичную ссылку — покупатель открывает в браузере
→ Интерактивный дашборд, можно фильтровать

**Экспорт PDF:**
**File → Print to PDF** → Layout: Landscape → всё в один файл

---

## Важные лайфхаки Tableau

| Проблема | Решение |
|----------|---------|
| SUM вместо отдельных значений | Правая кнопка на таблетке → **Dimension** |
| Дата группируется по году | Правая кнопка → выбери **Day** (нижний, зелёный) |
| Ось Y перевёрнута | Правая кнопка на оси → Edit axis → Scale → **Reversed** |
| Слишком много цветов | Filters → добавь `feed_type`, оставь один |
| Бары горизонтальные | Swap Rows and Columns (иконка в тулбаре) |
