# Model server + backend

Подготовлено 17.10.2026. **AWS, GPU inference, Docker build/up не запускались. Коммитов нет.**

Один корневой `docker-compose.yml`: приложение на порту **8000**, vLLM без опубликованных портов.
Backend скопирован без изменений из `origin/backend`, commit
`fc1af4d3660b942c9aa27502cbcd2bec71fb116b`. Источник фиксирует `deploy/backend-source.json`;
`deploy/export_backend.py` воспроизводит копию и отказывается перезаписывать изменённые файлы.
Копия `service/` исключена из Git; ветка backend не менялась.

Полные SHA весов, лицензии, источники поддержки и исключения: [матрица совместимости](../../analysis/VLLM_COMPATIBILITY.md).
Машиночитаемый каталог: [models.json](models.json).

## Пресеты

Ровно шесть `first_wave` и один `optional`. Остальные сохранены как `not_first_wave`, включая
MiniCPM-V-4.7, Cosmos3-Nano, GLM-4.6V-Flash, Qwen3.5-122B и прежний MiniCPM-V-4_5.
Все семь выбранных моделей используют **vLLM 0.31.0 / Transformers 5.17.0**.
Базовый образ закреплён digest в каталоге, Compose и Dockerfile.

Общие аргументы:

```text
--dtype bfloat16
--max-num-seqs 8
--max-model-len 65536
--limit-mm-per-prompt {"image":160,"video":1}
--max-num-batched-tokens 8192
--gpu-memory-utilization 0.90
--generation-config vllm
--default-chat-template-kwargs {"enable_thinking":false}
```

`--revision` и `--tokenizer-revision` берутся из каталога; TP — из пресета.
`eval`: `VLM_ENFORCE_EAGER=1`, добавляется `--enforce-eager`.
`final`: `VLM_ENFORCE_EAGER=0`, флаг отсутствует, CUDA graphs разрешены.
Переменная `VLM_ENFORCE_EAGER`, если задана непустой, переопределяет профиль.
При `--profile final` генератор создаёт согласованные настройки с `0`.

Qwen: `--mm-processor-kwargs '{"min_pixels":400000,"max_pixels":524288}'`.
Минимальный бюджет нужен, чтобы округление по сетке патчей тоже не уменьшало 464×848.
Получается 476×868 у Qwen2.5 и 480×864 у Qwen3 для отдельного изображения.
В приложении задан `FRAME_MAX_SIDE=1024`, иначе backend заранее уменьшал кадр до 640 px.

**InternVL — исключение:** `max_pixels` здесь не является настройкой процессора.
Используются 448px tiles, `min_dynamic_patch=4` через `--hf-overrides`, canvas 896×1792
для картинки 464×848, плюс thumbnail. В native video vLLM 0.31.0 использует один tile
448×448 на кадр; исходное разрешение native video этот пресет не сохраняет.
Backend передаёт кадры как картинки и этим ограничением native video не затрагивается.
`--mm-encoder-tp-mode data` нужен, чтобы vision encoder с 25 attention heads не делился на TP=2.
Контекст весов — 40 960; для требуемых 65 536 добавлен **экспериментальный YaRN factor=2**
по рекомендации авторов базового Qwen3-32B. Это не подтверждённый авторами InternVL режим 64K:
нужна проверка запуска и качества. Полный JSON override напечатает `serve.py --dry-run`.

FP8 235B: формат определяется из config весов автоматически; BF16 относится к вычислениям,
отдельная конвертация весов в BF16 не запрашивается.

## Подготовка локально, без запуска

Из корня репозитория (в Windows заменить `python3` на `python`):

```bash
python3 deploy/export_backend.py
python3 deploy/vllm/serve.py --model Qwen/Qwen3-VL-32B-Instruct --profile eval --write-env .env
python3 deploy/vllm/serve.py --model Qwen/Qwen3-VL-32B-Instruct --profile eval --dry-run
docker compose --env-file .env config --quiet
```

Генератор `.env` выбирает runtime/TP, создаёт случайный `API_KEY`, не печатает секрет и
не перезаписывает существующий файл. Для final можно создать отдельный `.env.final`:

```bash
python3 deploy/vllm/serve.py --model Qwen/Qwen3-VL-32B-Instruct --profile final --write-env .env.final
```

При смене модели создавай новый env-файл целиком: не оставляй TP или runtime от предыдущей модели.
`serve.py --dry-run` читает аргументы CLI и окружение, самостоятельно `.env` не загружает.
Compose получает `.env` автоматически либо явно через `--env-file`.

## Перенос без коммита

Обычный `git clone` пока не содержит эти незакоммиченные файлы. Для этого предусмотрен bundle:

```bash
python3 deploy/ec2/package.py
```

Архив `results/forte-deploy.tar.gz` содержит deployment, Compose и пример env;
не содержит `.env`, датасет, веса, логи, `.git`. Загрузи архив на **уже созданный** GPU-сервер,
распакуй в отдельную папку. Bootstrap склонирует репозиторий в указанную директорию,
наложит файлы bundle и восстановит pinned backend. Различающиеся существующие файлы
не перезаписываются. Эти команды ниже **здесь не выполнялись**:

```bash
mkdir -p ~/forte-bundle
tar -xzf forte-deploy.tar.gz -C ~/forte-bundle
bash ~/forte-bundle/deploy/ec2/bootstrap.sh --check-only
bash ~/forte-bundle/deploy/ec2/bootstrap.sh \
  --repo-dir ~/datathon26 --model Qwen/Qwen3-VL-32B-Instruct --profile eval
```

Нужны Ubuntu NVIDIA Deep Learning AMI, работающий Docker
Compose v2+, NVIDIA Container Toolkit, git, Python3; пользователь должен иметь доступ к Docker.
Bootstrap проверяет инструменты, собирает контейнеры, проверяет runtime/GPU count,
скачивает выбранную ревизию в `hf-cache`, выполняет `compose up --wait`, проверяет
vLLM `/health` и app `/api/v1/health`, запускает три smoke-запроса.
Существующий `.env` используется без изменений и имеет приоритет над `--model/--profile`.
Docker healthwait по умолчанию 3600 секунд; `FORTE_WAIT_SECONDS` меняет timeout.
Никаких вызовов создания/остановки EC2 в скрипте нет.
Кеш находится в Docker volume `hf-cache`, обычно на диске Docker data-root. Для 235B FP8
нужно место под сотни гигабайт весов и Docker-образы; GPU memory не заменяет дисковый объём.

## Backend и smoke

App использует `VLM_BACKEND=openai`, `OPENAI_BASE_URL=http://vlm:8000/v1`,
`OPENAI_MODEL=${VLM_MODEL}`, `WINDOW_CONCURRENCY=6`.
Это OpenAI-совместимый протокол к своему vLLM; облачный OpenAI API не используется.
Backend не отправляет Bearer-key: vLLM без API key и без host port; внешнее приложение
проверяет `X-API-Key`, взятый из `.env`. Health endpoint доступен без ключа.
Backend отправляет timestamp + JPEG для каждого кадра; переход на `video_url` в нём не делался.

Smoke создаёт две PNG и MP4 464×848, 6 секунд, 12 FPS, 72 кадра, без звука:
два секунды красного, зелёного, синего. Проверки:

1. `images`: две картинки в одном запросе → red, blue.
2. `video`: MP4 как `video_url` data URI → red, green, blue по порядку.
3. `mixed`: две картинки **и MP4 вместе** в одном user message / HTTP request.

```bash
# После запуска сервера; исполняется внутри app, где уже установлен ffmpeg.
docker compose exec -T app python /opt/forte/smoke_multi_image.py \
  --mode all --base-url http://vlm:8000/v1 --output-dir /data/smoke/manual
```

Все запросы, сырые ответы, MP4 и summary сохраняются; неверный порядок, HTTP error,
неполный ответ из-за token limit приводят к nonzero exit. `--dry-run` генерирует только fixtures
и payloads. Успех цветового smoke проверяет минимальный контракт, а не качество детекции нарушений.

## Что проверено здесь

- 14 развёрнутых Compose-конфигураций: 7 моделей × eval/final; порт, TP, модель и окружение.
- SHA/licence по HF metadata; архитектуры, processor paths, mixed input по source v0.31.0.
- Все семь pinned chat templates отрендерили две картинки и видео вместе (Jinja, без токенизации vLLM).
- `bash -n` bootstrap; Python syntax; pinned backend экспортирован побайтово.
- Реально закодирован и декодирован synthetic H.264 MP4, проверены 72 кадра/разрешение/порядок цветов.
- Три HTTP smoke через локальный CPU stub; неверные/обрезанные ответы отвергаются.
- **Настоящий backend** с CPU stub вместо vLLM: health, 401 без ключа, upload 202,
  обработка job до `done`, JPEG нескольких кадров без уменьшения 464×848.

Отчёты: `analysis/vllm_config_validation.json`, `analysis/vllm_cpu_validation.json`,
`analysis/vllm_template_validation.json`.
Повтор CPU integration: `python deploy/validate_cpu.py` (CPU requirements backend +
`imageio-ffmpeg`, `httpx`; никогда не загружает модель).

## Что остаётся проверить на GPU

Docker build/image pull, драйвер/CUDA, загрузка каждого checkpoint, реальное принятие и ответы
трёх типов запросов, FP8 kernels, TP2/TP4, VRAM/KV cache и стартовое multimodal profiling,
скорость/точность на датасете, параллельность 6/8, CUDA graphs в final, InternVL YaRN64K.
**160 images + 1 video — лимит количества вложений, а не гарантия вместимости в 65 536 tokens.**
Токены текста, картинок, видео и ответа суммируются; 160 полноразмерных кадров могут превысить
контекст, а восемь длинных запросов — доступную память. Обычные окна backend намного короче.
Подбор серверов соответствует заданию; фактическая вместимость этих режимов пока не измерена.
