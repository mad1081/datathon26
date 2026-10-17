# Сервис проверки кассовой дисциплины по видео (baseline v0)

Это локальный сервис для ForteBank Datathon 26. Пользователь загружает видео (.mov) через веб-интерфейс на русском или через API и получает:
- вердикт;
- нарушения с типом, таймкодом и описанием;
- 1–3 кадра-доказательства;
- ссылку на норму РК (акт, номер, пункт, дословная цитата).

Облачный AI не используется. Лица не распознаются, звук не анализируется.

```
service/
  app/main.py              FastAPI: UI (/), API (/api/v1/analyze, /api/v1/jobs/{id}, /api/v1/health)
  app/jobs.py              фоновая очередь + хранение задач на диске (DATA_DIR/jobs/<id>/job.json)
  app/config.py            все настройки через переменные окружения
  app/pipeline/video.py    декодирование (OpenCV, перекодирование ffmpeg при необходимости)
  app/pipeline/backends.py VLM: mock | transformers | openai (локальный vLLM)
  app/pipeline/prompts.py  строгий JSON-промпт с таксономией из rules.json
  app/pipeline/analyzer.py окна → агрегация → уточнение таймкода → кадры → нормы → вердикт
  app/pipeline/aggregate.py, parse.py, rules.py
  app/pipeline/timeline.py точка расширения: детекторы/трекер + правила на таймлайне
  app/static/index.html    одностраничный UI (рус.)
  rules.json               таксономия + нормы (источник истины; /workspace/datathon/rules.json — симлинк)
  eval/eval.py, labels.json  оценка на обучающих видео
  tests/make_synthetic.py  синтетические тестовые .mov
```

## Пайплайн v0
1. Видео декодируется с частотой `SAMPLE_FPS` (2 кадра/с), кадры уменьшаются до 640 px по длинной стороне.
2. Скользящие окна `WINDOW_SEC`=4 с с шагом `STRIDE_SEC`=2 с, до 8 кадров в окне. Каждый кадр подписан меткой времени. VLM возвращает строгий JSON `{scene, events:[{type, confidence, start_sec, end_sec, peak_sec, evidence}]}`. Таксономия лежит в system-промпте, чтобы локальный сервер мог кэшировать её как префикс.
3. Агрегация: события одного типа склеиваются, если окна пересекаются или разрыв ≤ 2 с. Оценка: `score = max_conf × (0.6 + 0.4 × доля окон, подтвердивших событие)`.
4. Уточнение таймкода:
   - вокруг пика (±2.5 с) модель проверяет каждый кадр отдельно, с частотой `REFINE_FPS`=4 кадра/с;
   - момент начала нарушения = первый кадр, где признак подтверждён;
   - внутри интервала от последнего «нет» до первого «да» берётся кадр с максимальным изменением картинки на полной частоте кадров. Это даёт точный кадр.
5. Кадры-доказательства: «до» (−1.5 с), «момент события», «после» (+1.5 с или конец события). JPEG в base64, кадры в полном разрешении (до 1280 px).
6. Тип события сопоставляется с правилом из rules.json: название, описание, нормы.
   - Вердикт `violation`, если хотя бы одно событие ≥ порога правила и правило учитывается в вердикте.
   - Что ниже порога, но ≥ `LOW_THRESHOLD`=0.35, попадает в `observations`. Ничего не отбрасывается молча.
   - Пропущенные или неразобранные окна видны в `meta.unanalyzed_ranges` и `meta.warnings`.
7. Лимит времени: `TIME_BUDGET_SEC`=270 с (по условиям кейса — до 5 минут на видео).
   - После первых окон сервис замеряет скорость модели.
   - Если оставшиеся окна не успевают, они укрупняются. Видео всё равно покрывается целиком, сервис пишет об этом предупреждение.

## API
Все `/api/*` (кроме health) требуют заголовок `X-API-Key` (ключ задаётся переменной окружения `API_KEY`).

```bash
curl -X POST -H "X-API-Key: $API_KEY" -F file=@video.mov http://HOST:8000/api/v1/analyze
# -> 202 {"job_id":"...","status":"processing"}
curl -H "X-API-Key: $API_KEY" http://HOST:8000/api/v1/jobs/<job_id>
# -> {"job_id","status":"processing"|"done"|"failed","verdict":"violation"|"no_violation",
#     "violations":[{"type","timecode_sec","description","evidence_frames":[{"timestamp_sec","image_base64"}...]}],
#     + доп. поля: type_id, timecode, frame_index, confidence, observed, rule{citations[]}, observations, meta}
```

**Поле `type` и `type_id`.** По ТЗ в `type` должно быть «Название типа нарушения», поэтому там русское название типа (`name_ru` из `rules.json`), например `"Наличные/ценности оставлены без присмотра"`. Машинный ключ того же типа (`cash_unattended`, `door_left_open` и т.д.) лежит в отдельном поле `type_id`. Логику (UI, eval, сравнение с разметкой) строить по `type_id`, название может меняться. Переменная `TYPE_FIELD=id` вернёт старое поведение (ключ в `type`), по умолчанию `name`.
`?full=false` вернёт только обязательные поля схемы.

Обязательные поля схемы жюри (`job_id`, `status`, `verdict`, `violations[].type/timecode_sec/description/evidence_frames`) не меняются. `verdict` бывает только `violation` или `no_violation`. Поля ниже необязательные (их использует UI, контракт совпадает с `review/forte_mockup.html`):

| Поле | Где | Что это |
|---|---|---|
| `confidence` | у каждого нарушения | число 0–1, итоговая уверенность |
| `window_sec` | у каждого нарушения | `[start, end]` — интервал, в котором модель видела признак |
| `rule_ref` | у каждого нарушения | `{doc, clause, quote, url}`: основная норма (дословная цитата из `rules.json`), `null`, если нормы нет |
| `rule_refs_extra` | у каждого нарушения | дополнительные нормы в том же формате (есть, только если норм больше одной) |
| `rule_status` | у каждого нарушения | есть, только если `rule_ref` = null: `rule_not_found_manual_review` или `vlm_type_outside_rule_base` |
| `source` | у каждого нарушения | `vlm` |
| `tracks` | верхний уровень | `[{label, start_sec, end_sec}]` — интервалы состояний сцены: `client_at_window`, `cashier_at_desk`, `cash_in_hands`, `counting`, `second_employee`, `phone`. Строятся как объединение окон, в которых VLM отметил состояние (`states` в ответе на каждое окно). В mock-режиме это детерминированные правдоподобные значения, а не детекция |
| `unanalyzed_ranges` | верхний уровень | `[{start_sec, end_sec, reason}]` — отрезки, которые модель не посмотрела (ошибка декодирования или модели, бюджет времени). Нарушение внутри них не исключено |
| `needs_manual_review` | верхний уровень | `true`, если есть непроанализированные отрезки, нарушения с косвенной или ненайденной нормой, тип `other` или (при `no_violation`) наблюдения с уверенностью ≥ 0.5. Третьего вердикта нет |
| `manual_review_reasons` | верхний уровень | список причин для `needs_manual_review` |

Пример фрагмента:
```json
{"job_id":"…","status":"done","verdict":"violation","needs_manual_review":false,
 "violations":[{"type":"Наличные/ценности оставлены без присмотра","type_id":"cash_unattended","timecode_sec":9.3,"description":"…","evidence_frames":[{"timestamp_sec":9.3,"image_base64":"…"}],
   "confidence":0.82,"window_sec":[7.5,12.0],
   "rule_ref":{"doc":"Правила осуществления кассовых операций…","clause":"п. 20 ч. 2","quote":"На рабочем месте кассового работника…","url":"https://adilet.zan.kz/rus/docs/V1900019680"}}],
 "tracks":[{"label":"cashier_at_desk","start_sec":0,"end_sec":8},{"label":"cash_in_hands","start_sec":4,"end_sec":9}],
 "unanalyzed_ranges":[]}
```

## Запуск на CPU (mock-режим, без модели) — проверено на боксе
Mock-модель ищет на кадре насыщенно-красный объект. Она нужна только для проверки пайплайна, UI и API.
```bash
cd /workspace/datathon
python3 -m venv .venv && .venv/bin/pip install -r service/requirements.txt
cd service
../.venv/bin/python tests/make_synthetic.py tests/data
API_KEY=test-key VLM_BACKEND=mock ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# UI: http://localhost:8000/   (ввести ключ test-key, загрузить tests/data/violation.mov)
```

## Запуск с реальной моделью (GPU)
**Вариант A (рекомендуется): vLLM + приложение, docker compose**
```bash
cd service && API_KEY=secret docker compose up -d --build     # VLM_MODEL=... для смены модели
```
**Вариант B: transformers в одном процессе**
```bash
pip install -r requirements.txt -r requirements-gpu.txt   # + torch с CUDA
API_KEY=secret VLM_BACKEND=transformers VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
  VLM_FALLBACK_MODEL=Qwen/Qwen3-VL-4B-Instruct uvicorn app.main:app --host 0.0.0.0 --port 8000
```
**Вариант C: vLLM запущен вручную**
```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct --max-model-len 16384 --limit-mm-per-prompt '{"image":10}' --enable-prefix-caching --port 8001
API_KEY=secret VLM_BACKEND=openai OPENAI_BASE_URL=http://127.0.0.1:8001/v1 WINDOW_CONCURRENCY=6 uvicorn app.main:app --port 8000
```
`OPENAI_BASE_URL` обязан указывать на локальный сервер: код отклоняет публичные хосты.

Публичный URL для жюри (обязателен по условиям кейса):
- поднять сервис на GPU-машине с белым IP;
- или пробросить порт 8000 туннелем (cloudflared/ngrok). Через туннель идёт только HTTP-трафик сервиса, модель остаётся локальной.

### Требования к GPU (оценка, на реальном железе не замерялось)
| Модель | Лицензия | VRAM (bf16) | Минимальная GPU |
|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct (по умолч.) | Apache-2.0 | ~17 ГБ веса + 3–6 ГБ KV | 24 ГБ (L4, A10G, RTX 3090/4090); комфортно — 40–48 ГБ (A100 40G, L40S) |
| Qwen/Qwen3-VL-8B-Instruct | Apache-2.0 | ~18 ГБ | 24 ГБ+ |
| Qwen/Qwen3-VL-4B-Instruct (fallback) | Apache-2.0 | ~9 ГБ | 16 ГБ (T4 — только fp16, медленно) |
| ~~Qwen2.5-VL-3B-Instruct~~ | **Qwen Research (некоммерческая)** | — | **не использовать**: нарушает требование о коммерческой лицензии |

Объём запроса на одно окно: ~2.9k токенов текста (кэшируется как префикс) + 8 кадров × ~300 токенов. На 60-секундное видео приходится ~29 окон и 20–40 проверочных вызовов.
- vLLM на L4/A10G с `WINDOW_CONCURRENCY=6`: ожидается около 1–2 мин на видео.
- transformers без батчинга: 3–5 мин, есть риск не уложиться в лимит. Поэтому для финала рекомендован vLLM.

Ориентировочное время обработки при необходимости ужимается до лимита адаптивным укрупнением окон (см. п. 7 пайплайна).

## Оценка
```bash
# видео в /workspace/datathon/data/ (имена вида X-12.mov или с кириллической Х-12.mov; иначе --mapping file.csv: filename,X-номер)
# метка — секунда, список секунд (одинаковые файлы X-4/X-47) или null; --typed labels_typed.csv добавляет сверку типа (type_hit)
VLM_BACKEND=openai OPENAI_BASE_URL=... ../.venv/bin/python -m eval.eval --data /workspace/datathon/data
# или через работающий сервис:
../.venv/bin/python -m eval.eval --data /workspace/datathon/data --api http://127.0.0.1:8000 --key test-key
```
Метрики: точность вердикта, TP/FP/FN/TN, recall, precision, MAE таймкода, доля попаданий в ±2 с, максимальное время обработки. Результаты пишутся в `eval/out/<время>/`.

## Основные настройки (env)
`API_KEY`, `UI_API_KEY` (подставить ключ в UI), `DATA_DIR`, `RULES_PATH`, `VLM_BACKEND`, `VLM_MODEL`, `VLM_FALLBACK_MODEL`,
`OPENAI_BASE_URL`, `OPENAI_MODEL`, `WINDOW_CONCURRENCY`, `SAMPLE_FPS`, `WINDOW_SEC`, `STRIDE_SEC`, `MAX_WINDOWS`,
`FRAME_MAX_SIDE`, `REFINE`, `REFINE_FPS`, `REFINE_SPAN_SEC`, `LOW_THRESHOLD`, `THRESHOLD_OFFSET` (сдвиг всех порогов),
`TIME_BUDGET_SEC`, `MAX_VIOLATIONS`, `TYPE_FIELD` (`name` — рус. название в поле `type`, `id` — машинный id), `MOCK_DELAY`.

## Расширение (следующий шаг)
`app/pipeline/timeline.py` задаёт интерфейсы `SignalProvider` (детекция и трекинг по кадрам) и `TimelineRule` (правило на таймлайне → `Candidate`).
- Кандидаты от этих правил сливаются с кандидатами VLM в `analyzer.py`.
- Детекторы можно брать с лицензиями Apache/MIT: RT-DETR (lyuwenyu, Apache-2.0), Grounding DINO (Apache-2.0), MediaPipe (Apache-2.0).
- **Ultralytics YOLO не использовать: лицензия AGPL.**
