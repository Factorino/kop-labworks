# Правила разработки

## Подготовка

Нужны [uv] и [just]. Python нужной версии (`.python-version`) uv скачает сам.

```bash
just sync     # зависимости из uv.lock в .venv
just hooks    # git-хуки pre-commit, commit-msg и pre-push
```

| Хук | Когда | Что проверяет |
| --- | --- | --- |
| `pre-commit` | Перед коммитом | Гигиена файлов (пробелы и перевод строки в конце, LF, синтаксис YAML/JSON/TOML, конфликты слияния, закрытые ключи); ruff, mypy, import-linter; согласованность `uv.lock` с `pyproject.toml` |
| `commit-msg` | После ввода сообщения | Формат сообщения коммита (ниже) |
| `pre-push` | Перед отправкой | Тесты |

## Команды

| Команда | Что делает |
| --- | --- |
| `just check` | Линтеры, типы, контракт слоёв и тесты — то же, что в CI |
| `just fix` | Автоисправления ruff и форматирование |
| `just test` | Тесты; также `just test -m unit`, `just test tests/integration -x` |
| `just cov` | Покрытие с порогом из `.coveragerc` |
| `just pre-commit` | Все хуки по всем файлам |
| `just lock` | Пересобрать `uv.lock` после правки `pyproject.toml` |
| `just --list` | Все остальные команды |

Зависимости добавляются через `uv add` (или `uv add --group <группа>`),
`uv.lock` коммитится вместе с `pyproject.toml`.

## Docker

`just init` создаёт из шаблонов `*.example` конфигурацию приложения для
окружений (`.config/local.toml`, `.config/development.toml`), переменные
compose (`.config/compose.env`) и секреты (`.secrets/*`); существующие файлы не
перезаписываются. Значения `change-me` заменяются перед первым запуском; сами
файлы в git не попадают.

Окружения совпадают со значениями настройки `Environment` приложения.

| Окружение | Где работают процессы приложения | Compose |
| --- | --- | --- |
| `local` | На хосте (`just run`, конфигурация `.config/local.toml`); в контейнерах только инфраструктура с портами на `127.0.0.1` | `docker-compose.yml` + `docker-compose.local.yml` |
| `development` | В контейнерах вместе с инфраструктурой (конфигурация `.config/development.toml`); образ пересобирается из рабочей копии при каждом `just up development` | `docker-compose.yml`, профиль `app` |
| `testing` | В контейнере тестов рядом с временной инфраструктурой | `docker-compose.testing.yml`, отдельный проект |
| `staging`, `production` | Появятся вместе с образом, который есть что развернуть | — |

`local` и `development` — один compose-проект: контейнеры и данные общие,
переключение пересоздаёт только изменившиеся контейнеры. `just up` в `local`
удаляет контейнеры процессов приложения, чтобы они не занимали порты тех же
процессов на хосте, и отказывается запускать их по имени (`just up local api`).

Окружение — первый аргумент команды, по умолчанию `local`; всё после него
передаётся docker compose как есть: имена сервисов и флаги.

| Команда | Что делает |
| --- | --- |
| `just up [local\|development] [сервис...]` | Запуск в фоне с ожиданием готовности: `just up`, `just up development postgresql` |
| `just stop`, `just restart` | Остановка и перезапуск: `just restart local rabbitmq` |
| `just logs`, `just ps` | Журналы и список контейнеров: `just logs local redis` |
| `just down [local\|development]` | Удаление контейнеров; тома сохраняются |
| `just teardown` | Стек приложения и тестовый стек вместе с томами |
| `just build` | Runtime-образ `kop-labworks:local` с метками версии и коммита |
| `just test-container` | Окружение `testing`: тесты в образе рядом с временными PostgreSQL, Redis и RabbitMQ; после прогона всё удаляется |

Базовые образы закреплены по digest; поверх базового образа ставятся
обновления безопасности Debian.

## Процессы на хосте

В окружении `local` процессы приложения запускаются из рабочей копии. Список
процессов — в `Procfile`; их имена совпадают с именами сервисов в compose.

| Команда | Что делает |
| --- | --- |
| `just run` | Все процессы из `Procfile` в одном терминале; Ctrl+C останавливает все |
| `just run api` | Только перечисленные процессы; API перезагружается сам при изменении кода |
| `just migrate` | Применить миграции |
| `just revision "описание"` | Создать миграцию по изменениям моделей |
| `just cli ...` | Любая команда `kop-cli`: `just cli db current` |

Порядок работы: `just up` (инфраструктура), `just migrate`, `just run`.

## Архитектура

Пакет `src/kop` разделён на слои. Правило зависимостей проверяет import-linter
(`.importlinter`) в составе `just check`:

```text
main  ->  presentation | infrastructure  ->  application  ->  domain
```

Зависимости направлены только вниз; `presentation` и `infrastructure` друг
друга не импортируют. Назначение каждого слоя описано в его `__init__.py`.

Внешние импорты `domain` и `application` ограничены белым списком: стандартная
библиотека разрешена всегда, остальные пакеты — только перечисленные в
`.importlinter` (`domain` — `typing_extensions`; `application` — ещё `pydantic`
и `structlog`). Новая зависимость недоступна этим слоям, пока её явно не
добавят в список. Тип контракта реализован в `scripts/import_contracts.py`.

## Соглашения кода

**Порядок элементов.** В модуле: docstring, `from __future__`, импорты тремя
блоками (стандартная библиотека, сторонние пакеты, проект), блок
`TYPE_CHECKING`, `__all__`, логгер, константы, изменяемое состояние, типы,
исключения, классы, публичные функции, protected, private, точка входа. В
классе: docstring, константы, атрибуты, `__init__`, dunder-методы,
`classmethod`, `staticmethod`, `property`, публичные методы, protected,
private. Правило зависимостей важнее буквального порядка: используемое
объявляется раньше использующего — поэтому `_between` в
`readers/base.py` стоит выше таблицы `_OPERATORS`, которая на него ссылается.

**Имена классов.**

| Префикс | Для чего | Примеры |
| --- | --- | --- |
| `I` | Протоколы | `IClock`, `IMigrator`, `ITraceProvider` |
| `Abstract` | Абстрактные классы | `AbstractTransactionManager` |
| `Base` | Базовые реализации; после технологического префикса | `BaseORM`, `SABaseReader`, `SABaseRepository` |
| — | Корни семейств и конкретные классы | `Entity`, `ValueObject`, `DTO`, `Interactor`, `SATransactionManager` |

Флаг-объявление, которое переставляют наследники, пишется sunder, а не
константой: `_abstract_` в `DTO` и его абстрактных потомках.

**Порты.** Порт объявляется в том слое, который его вызывает, а не в том,
который его реализует. `IDependencyProbe` лежит в `application`, потому что его
зовёт интерактор `CheckReadiness`; `IMigrator` и `ITraceProvider` — в
`presentation`, потому что их зовут команда CLI и middleware. Если порт лежит в
слое, который реализации импортировать нельзя, соответствие остаётся
структурным: `AlembicMigrator` не наследует `IMigrator`, а совпадение проверяет
mypy в провайдере `main`, где встречаются обе стороны.

**Ошибки.** Иерархия — в `domain/errors`, `application/errors` и
`infrastructure/errors`; слой ошибки говорит о её роде, а не о месте выброса.
Текст сообщения начинается с заглавной буквы, поэтому имена сущностей в
`__entity__` тоже пишутся с заглавной: шаблон `"{entity} already exists"`
подставляет их первым словом. Сообщение собирается из полей класса, а поля
задаёт наследник:

```python
@error
class UsernameAlreadyExistsError(AlreadyExistsError):
    code: ClassVar[str] = StatusCode.USERNAME_ALREADY_EXISTS_ERROR
    msg: str = "{entity} with username={username} already exists"

    entity: str = "User"
    username: str
```

У `AlreadyExistsError` конфликтующие поля можно передать и киваргами
(`AlreadyExistsError(entity="User", email="a@b.c")`) — так их передаёт
трансляция ошибок БД, которая узнаёт список колонок только во время
выполнения. Всё, что попало в ошибку, видно в `context`, то есть в поле
`detail` ответа API.

## CLI

`kop-cli` собран так же, как HTTP-часть: дерево команд — в `presentation/cli`,
привязка к реализациям — в `main`.

| Что | Где |
| --- | --- |
| Команды как объекты (`execute`) | `presentation/cli/commands/` |
| Дерево typer, флаги и рендеры | `presentation/cli/app.py` |
| Запуск команды, обработка ошибок, коды возврата | `presentation/cli/runner.py`, `exit_codes.py`, `handlers/` |
| Вывод: темы, консоли, writer | `presentation/cli/styles.py`, `console.py`, `io/output.py` |
| Тексты сообщений и справки | `presentation/cli/constants.py` |
| Конфигурация, логирование, контейнер dishka | `main/cli/entrypoint.py`, `main/cli/container.py`, `main/di/providers/cli.py` |

Конфигурация читается лениво, при запуске самой команды, поэтому
`kop-cli db --help` работает и без неё. Результат команды уходит в stdout
(`kop-cli db current` можно передать по конвейеру), всё остальное — в stderr.

| Код возврата | Когда |
| --- | --- |
| `0` | Успех |
| `1` | `ValidationError` — команду попросили о невозможном |
| `2` | Конфигурацию не удалось прочитать |
| `3`, `4` | `NotFoundError`; `AlreadyExistsError` и `ConflictError` |
| `5` | Прочие ошибки приложения, включая инфраструктурные |
| `70` | Исключение не из нашей иерархии |
| `130` | Прерывание с клавиатуры |

## Тесты

| Каталог | Что допустимо |
| --- | --- |
| `tests/unit` | Код без ввода-вывода: `domain`, `application` и чистые функции остальных слоёв; без сети и базы данных |
| `tests/integration` | Адаптеры инфраструктуры против реальных зависимостей |
| `tests/e2e` | Приложение целиком через внешний интерфейс |

Маркеры `unit`, `integration` и `e2e` ставятся автоматически по каталогу
(`tests/conftest.py`), поэтому `-m "not e2e"` работает без ручной разметки.

Тестам, которым нужна база данных, её называет переменная
`KOP_TEST_DATABASE_URL`; без неё они пропускаются с указанием причины.

| Где | Откуда база |
| --- | --- |
| На хосте | `just up`, затем `eval "$(just test-db)"`: база `kop_tests` в PostgreSQL стека, отдельно от данных приложения |
| `just test-container` | Временный PostgreSQL тестового стека |
| CI | Сервис PostgreSQL в джобах `test` и `metrics` |

Порог покрытия в `.coveragerc` (сейчас 85 %) считается вместе с
интеграционными и сквозными тестами и поднимается вместе с тестами каждой
функции.

## Коммиты

Формат — [Conventional Commits][cc]:

```text
<тип>(<область>): <что сделано>

<необязательное тело: зачем и почему>

<необязательные сноски: BREAKING CHANGE, Refs>
```

Примеры:

```text
feat(posts): add post publishing to selected channels
fix(telegram): retry on 429 with the delay from retry_after
ci: run tests on python 3.13
```

| Тип | Когда | Версия при выпуске |
| --- | --- | --- |
| `feat` | Новая функция | minor |
| `fix` | Исправление ошибки | patch |
| `perf` | Ускорение без изменения поведения | patch |
| `refactor` | Изменение кода без изменения поведения | patch |
| `test` | Тесты | — |
| `docs` | Документация | — |
| `build` | Сборка, зависимости, Docker | — |
| `ci` | Пайплайны GitHub Actions | — |
| `style` | Форматирование | — |
| `chore` | Прочее обслуживание | — |
| `revert` | Отмена коммита | — |
| `bump` | Выпуск версии (создаёт commitizen) | — |

Несовместимое изменение отмечается `!` после типа или сноской
`BREAKING CHANGE:`. Пока версия `0.x`, оно повышает minor, а не major.

Сообщения коммитов пишутся на английском, в повелительном наклонении, со
строчной буквы и без точки в конце. Формат можно не запоминать:
`just commit` спросит каждую часть по очереди.

## Ветки

| Ветка | Назначение | Создаётся от | Сливается в |
| --- | --- | --- | --- |
| `master` | Выпущенные версии | — | — |
| `backend` | Разработка серверной части | `master` | `master` при выпуске |
| `frontend` | Разработка веб-интерфейса | `master` | `master` при выпуске |
| `<тип>/<кратко>` | Одна задача | `backend` или `frontend` | ту же ветку |

Задачная ветка называется по типу основного изменения и короткому описанию
через дефис: `feat/auth`, `fix/vk-rate-limit`, `ci/pipelines`. Одна ветка —
одна задача; ветка живёт до слияния и затем удаляется.

`master`, `backend` и `frontend` защищены: изменения попадают в них только
через pull request после прохождения проверок; принудительная отправка
(`push --force`) и удаление запрещены.

## Pull request

1. Заголовок — в формате Conventional Commits: при слиянии задачной ветки он
   становится сообщением коммита. Проверку `commits` не пройдёт PR, у которого
   неверный заголовок или хотя бы один коммит.
2. Описание заполняется по шаблону. Задача YouTrack указывается строкой
   `Refs: KOP-NN`.
3. Слияние — после прохождения обязательных проверок.

| Что сливается | Способ | Почему |
| --- | --- | --- |
| Задачная ветка → `backend` / `frontend` | Squash and merge | Одна задача — один коммит в истории интеграционной ветки |
| `backend` / `frontend` → `master` | Create a merge commit | Выпуск версии остаётся виден в истории `master` вместе со всеми задачами |

Rebase and merge не используется.

## Непрерывная интеграция

| Workflow | Когда запускается | Что делает |
| --- | --- | --- |
| `commits.yml` | Pull request | Формат сообщений коммитов и заголовка PR |
| `ci.yml` | Pull request; push в `master` и `backend`; вручную | `lint` — все хуки pre-commit; `test` — тесты на Python 3.12 и 3.13, отчёты JUnit и покрытия в артефактах; `security` — аудит зависимостей; `docker` — тесты в образе, сборка runtime-образа и проверка trivy; `ci` — сводный результат |
| `release.yml` | Тег `v*` | Сверка тега с версией пакета, сборка wheel и sdist, GitHub Release с разделом из `CHANGELOG.md`; образ в GHCR с тегами версии, `major.minor` и коммита |
| `metrics.yml` | Тег `v*`; вручную | Срез метрик версии в артефактах (`scripts/metrics.py`) |

Обязательные проверки для слияния в `backend`: `commits` и `ci`.

## Выпуск версии

Номер версии и раздел `CHANGELOG.md` вычисляются из сообщений коммитов с
последнего тега. Поскольку ветки защищены, commitizen не создаёт коммит сам:
изменения проходят через pull request, а тег ставится после слияния.

```bash
# 1. Узнать номер следующей версии
git switch backend && git pull
just bump --dry-run

# 2. Обновить CHANGELOG.md, версию и метрики в отдельной ветке
git switch -c release/vX.Y.Z
just bump --files-only --yes
just lock             # версия проекта записана и в uv.lock
just metrics vX.Y.Z   # docs/metrics/vX.Y.Z.json и сводная таблица
git add -A
git commit -m "bump: version A.B.C -> X.Y.Z"
git push -u origin release/vX.Y.Z
# PR release/vX.Y.Z -> backend, Squash and merge

# 3. Поставить тег на результат слияния
git switch backend && git pull
git tag -a vX.Y.Z -m "bump: version A.B.C -> X.Y.Z"
git push origin vX.Y.Z
```

Тег `v*` запускает публикацию релиза и повторный срез метрик в CI. Метрики
снимаются до тега, на содержимом, которое затем получает тег: при squash-слиянии
код не меняется. Когда версия готова к выпуску целиком,
интеграционная ветка сливается в `master` через PR (Create a merge commit).

## Обновление хуков

```bash
uv run pre-commit autoupdate
```

После обновления `commitizen` в `.pre-commit-config.yaml` та же версия
указывается в `COMMITIZEN_VERSION` в `.github/workflows/commits.yml`, чтобы
хук и CI проверяли сообщения одинаково.

[uv]: https://docs.astral.sh/uv/
[just]: https://just.systems/
[cc]: https://www.conventionalcommits.org/ru/v1.0.0/
