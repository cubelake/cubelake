# Norway App Store — Looker Studio Setup

Полный гайд: от CSV до готового дашборда.
Looker Studio бесплатный, заходи на lookerstudio.google.com через Google аккаунт.

---

## Шаг 1 — Экспортируй CSV из DuckDB

Запусти каждый запрос из `norway_queries.md` и сохрани CSV:

| Файл | Запрос |
|------|--------|
| `norway_top_chart.csv` | Запрос 1 |
| `norway_trend.csv` | Запрос 2 |
| `norway_rising.csv` | Запрос 3 |
| `norway_genre_snapshot.csv` | Запрос 4 |
| `norway_genre_trend.csv` | Запрос 5 |
| `norway_developers.csv` | Запрос 6 |

---

## Шаг 2 — Создай отчёт и подключи данные

1. Открой **lookerstudio.google.com**
2. Нажми **Blank Report**
3. Появится окно "Add data to report"
4. Выбери коннектор **File Upload**
5. Загрузи первый CSV (`norway_top_chart.csv`)
6. Нажми **Add** → **Add to report**

> Повторяй для каждого CSV — каждый файл = отдельный Data Source.
> Добавить новый: Resource → Manage added data sources → Add a data source.

---

## Чарт 1 — Топ-чарт (Table)

**Data source:** `norway_top_chart.csv`

1. Insert → **Table**
2. Нарисуй прямоугольник на холсте
3. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `app_name`, `developer_name`, `genre` |
| Metric | `position`, `rating`, `price` |
| Sort | `position` → Ascending |
| Row numbers | ON |

4. **Style tab:**
   - Header → Background: тёмный цвет по вкусу
   - Rows per page: 20
   - Conditional formatting → `position` → Color scale: 1 = зелёный, 20 = красный

5. Добавь **Filter control:**
   - Insert → Filter control
   - Field: `feed_type`
   - Control type: Drop-down list

---

## Чарт 2 — Тренд позиций (Time Series)

**Data source:** `norway_trend.csv`

> SQL уже возвращает `(11 - chart_position)` как `position` — значение 10 = #1 место, линия вверх = рост.

1. Insert → **Time series**
2. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `snapshot_date` |
| Breakdown dimension | `app_name` |
| Metric | `position` |
| Sort | `snapshot_date` → Ascending |

3. **Style tab:**
   - Show data labels: OFF
   - Show points: ON
   - Line weight: 2px
   - Smooth lines: OFF (так лучше видны резкие изменения)
   - Y-axis → Min: `0`, Max: `11`
   - Y-axis → Axis title: `Rank (10 = #1)`

4. Добавь **Filter control:** `feed_type`

---

## Чарт 3 — Растущие приложения (Bar chart)

**Data source:** `norway_rising.csv`

1. Insert → **Bar chart**
2. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `app_name` |
| Breakdown dimension | `feed_type` |
| Metric | `avg_daily_delta` |
| Sort | `avg_daily_delta` → Descending |
| Bars | 15 |

3. **Style tab:**
   - Orientation: Horizontal (Bar → переключи)
   - Bar colors: free → синий `#4285F4`, paid → оранжевый `#FF6D00`
   - Show data labels: ON
   - Legend: Bottom

---

## Чарт 4 — Жанровый breakdown (Donut)

**Data source:** `norway_genre_snapshot.csv`

1. Insert → **Pie chart**
2. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `genre` |
| Metric | `pct_of_chart` |
| Sort | `pct_of_chart` → Descending |
| Max slices | 10 |

3. **Style tab:**
   - Donut: ON (выглядит чище чем pie)
   - Show legend: ON → Right
   - Slice labels: Percent

4. Добавь **Filter control:** `feed_type`

---

## Чарт 5 — Тренд жанров (Stacked area)

**Data source:** `norway_genre_trend.csv`

1. Insert → **Time series**
2. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `snapshot_date` |
| Breakdown dimension | `genre` |
| Metric | `pct_of_chart` |
| Sort | `snapshot_date` → Ascending |

3. **Style tab:**
   - Stacked area: ON
   - Show data labels: OFF
   - Y-axis → Axis title: `% of chart`
   - Legend: Bottom

4. Добавь **Filter control:** `feed_type`

---

## Чарт 6 — Разработчики (Bar chart)

**Data source:** `norway_developers.csv`

1. Insert → **Bar chart**
2. В панели справа:

| Поле | Значение |
|------|----------|
| Dimension | `developer_name` |
| Metric | `apps_in_chart` |
| Sort | `apps_in_chart` → Descending |
| Bars | 15 |

3. **Style tab:**
   - Orientation: Horizontal
   - Bar color: один цвет, например `#1A73E8`
   - Show data labels: ON
   - Legend: None

4. Добавь **Tooltip:** добавь `avg_position` и `avg_rating` как дополнительные метрики — они видны при наведении.

---

## Шаг 3 — Глобальные фильтры дашборда

Один фильтр `feed_type` управляет всеми чартами:

1. Insert → **Filter control**
2. Field: `feed_type`
3. Control type: Drop-down list
4. Default value: `free`
5. Выдели фильтр → правая кнопка → **Apply filter to all charts on page** ✓

---

## Шаг 4 — Оформление для продажи

### Заголовок
1. Insert → **Text**
2. Напиши: `Norway App Store Intelligence — [Month] [Year]`
3. Шрифт: 24px, Bold

### Подзаголовок
```
Free & Paid · Top 200 Apps · 30-day snapshot · Source: Apple App Store
```

### Цвета страницы
- Background: `#0D1117` (тёмный) или `#FFFFFF` (светлый)
- Theme: Insert → Theme and layout → выбери Midnight (тёмный) или Simple (светлый)

---

## Шаг 5 — Шаринг и экспорт

### Поделиться ссылкой (для покупателя)
- Share → **Manage access** → Anyone with link → Viewer
- Скопируй ссылку → отдай покупателю

### Экспорт PDF
- File → **Download** → PDF
- Format: A4 Landscape
- Pages: All pages

### Встроить на сайт
- File → **Embed report** → скопируй iframe код

---

## Структура страниц дашборда

Рекомендую разбить на 2 страницы:

**Page 1 — Overview**
```
[Заголовок + фильтр feed_type]
[Топ-чарт Table]         [Donut жанры]
[Тренд позиций Line]
```

**Page 2 — Deep Dive**
```
[Растущие приложения Bar]
[Тренд жанров Stacked area]
[Разработчики Bar]
```
