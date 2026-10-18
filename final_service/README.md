# Сервис проверки кассовой дисциплины по видео

Пользователь загружает видео (.mov/.mp4) через веб-интерфейс на русском или через API и получает вердикт,
нарушения (тип, таймкод, описание), 1–3 кадра-доказательства из исходного видео и ссылку на норму РК.
Модель работает локально (vLLM на том же сервере); облачный AI не используется. Лица не распознаются, звук не анализируется.

```
app/main.py                   FastAPI: UI (/), API (/api/v1/analyze, /api/v1/jobs/{id}, /api/v1/health)
app/jobs.py                   фоновая очередь (WORKERS потоков) + хранение задач на диске (DATA_DIR/jobs/<id>/job.json)
app/config.py                 все настройки через переменные окружения
app/pipeline/analyzer.py      Analyzer.run: декодирование -> анализ всего видео -> вердикт
app/pipeline/whole_video.py   один запрос к VLM по кадрам всего видео (или N запросов с голосованием), правила, доказательства
app/pipeline/frames.py        выборка кадров и кадры-доказательства (OpenCV, ffmpeg при необходимости)
app/pipeline/prompt.py        промпт: сценарии кассовых операций + закрытый перечень типов из rules.json
app/pipeline/vlm.py           клиент локального OpenAI-совместимого сервера (стриминг, повторы, проверка localhost)
app/pipeline/rules.py         rules.json: типы, пороги, нормы и цитаты
app/static/index.html         одностраничный UI
rules.json                    таксономия + нормы, v0.4
deploy/start.sh               vLLM + приложение в одном GPU-поде (см. deploy/README_DEPLOY.md)
tests/                        тесты (CPU, без модели) и fake_vlm.py — фиктивный OpenAI-совместимый сервер
```

## Пайплайн
1. Кадры всего видео: 2 кадра/с для видео короче 120 с, иначе 1 кадр/с; не больше `MAX_FRAMES`=250; 640 px по длинной стороне.
   Каждый кадр подписан временем `[t=12.0 с]`.
2. Один запрос к VLM со всеми кадрами. Ответ — JSON `{scenario, timeline[], violations[{type_id, timecode_sec, confidence, observed}]}`.
   При ошибке транспорта — до 2 повторов; при невалидном JSON — один повтор с temperature 0; если не помогло — задача `failed`.
   Если запрос не поместился в контекст модели — один повтор с 60% кадров.
3. `N_SAMPLES`>1: N параллельных запросов (temperature `SAMPLE_TEMPERATURE`=0.6); тип остаётся, если он есть в строгом большинстве ответов,
   таймкод — медиана. Если до лимита (5 минут от загрузки) осталось мало времени — один запрос.
4. В вердикт идут все типы из rules.json, кроме `other` и типов с `count_in_verdict=false`; порог = порог правила + `THRESHOLD_OFFSET`.
   Остальное — в `observations` с причиной.
5. Кадры-доказательства: −1.5 с, момент нарушения, +1.5 с из исходного видео (до 1280 px, JPEG base64).

## API
```bash
curl -H "X-API-Key: $API_KEY" -F file=@X-1.mov http://localhost:8000/api/v1/analyze
# -> 202 {"job_id":"...","status":"processing"}
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/jobs/<job_id>
# -> {"job_id","status":"processing"|"done"|"failed","verdict":"violation"|"no_violation",
#     "violations":[{"type","timecode_sec","description","evidence_frames":[{"timestamp_sec","image_base64"}]}],
#     + доп. поля: type_id, timecode, confidence, observed, rule{citations[]}, rule_ref, scenario, timeline, observations, meta}
# failed -> {"job_id","status":"failed","error":"..."}; без ключа / с неверным ключом -> 401
```

## Локальный запуск без GPU
```bash
pip install -r requirements.txt
python -m pytest -q tests                                   # mock, без модели
python tests/fake_vlm.py --port 8011 &                      # фиктивный VLM-сервер
API_KEY=test-key VLM_BASE_URL=http://127.0.0.1:8011/v1 VLM_MODEL=fake uvicorn app.main:app --port 8000
# или встроенный mock без сервера: VLM_BASE_URL=mock
```

## Основные настройки (env)
`API_KEY`, `VLM_BASE_URL` (только localhost / частные IP / имя docker-сервиса), `VLM_MODEL`, `DISABLE_THINKING`,
`N_SAMPLES`, `SAMPLE_TEMPERATURE`, `THRESHOLD_OFFSET`, `WORKERS`=2, `TIME_BUDGET_SEC`=285 (от загрузки),
`MAX_FRAMES`, `MAX_SIDE`, `FPS_SHORT`, `FPS_LONG`, `VLM_TIMEOUT`, `VLM_RETRIES`, `DATA_DIR`, `RULES_PATH`.
