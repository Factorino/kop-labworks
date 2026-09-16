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

## Архитектура

Пакет `src/kop` разделён на слои. Правило зависимостей проверяет import-linter
(`.importlinter`) в составе `just check`:

```text
main  ->  presentation | infrastructure  ->  application  ->  domain
```

Зависимости направлены только вниз; `presentation` и `infrastructure` друг
друга не импортируют. `domain` и `application` не импортируют фреймворки и
драйверы. Назначение каждого слоя описано в его `__init__.py`.

## Тесты

| Каталог | Что допустимо |
| --- | --- |
| `tests/unit` | Только `domain` и `application`; без сети, базы данных и файловой системы |
| `tests/integration` | Адаптеры инфраструктуры против реальных зависимостей |
| `tests/e2e` | Приложение целиком через внешний интерфейс |

Маркеры `unit`, `integration` и `e2e` ставятся автоматически по каталогу
(`tests/conftest.py`), поэтому `-m "not e2e"` работает без ручной разметки.
Порог покрытия в `.coveragerc` поднимается вместе с тестами каждой функции;
целевое значение — 80 %.

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

## Выпуск версии

Номер версии и раздел `CHANGELOG.md` вычисляются из сообщений коммитов с
последнего тега. Поскольку ветки защищены, commitizen не создаёт коммит сам:
изменения проходят через pull request, а тег ставится после слияния.

```bash
# 1. Узнать номер следующей версии
git switch backend && git pull
just bump --dry-run

# 2. Обновить CHANGELOG.md и версию в pyproject.toml в отдельной ветке
git switch -c release/vX.Y.Z
just bump --files-only --yes
just lock             # версия проекта записана и в uv.lock
git commit -am "bump: version A.B.C -> X.Y.Z"
git push -u origin release/vX.Y.Z
# PR release/vX.Y.Z -> backend, Squash and merge

# 3. Поставить тег на результат слияния
git switch backend && git pull
git tag -a vX.Y.Z -m "bump: version A.B.C -> X.Y.Z"
git push origin vX.Y.Z
```

Тег `v*` запускает публикацию релиза. Когда версия готова к выпуску целиком,
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
