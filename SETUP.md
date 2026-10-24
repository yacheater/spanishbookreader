# Настройка телефона и синхронизации (один раз, ~20 минут)

Всё бесплатно. Только **личные** аккаунты — не рабочие.
Как это устроено: код приложения лежит на GitHub и открывается как сайт (GitHub Pages);
тексты статей и твой прогресс хранятся в Supabase, и прочитать их можешь только ты после входа.
В публичный репозиторий тексты не попадают (`.gitignore`).

## 1. Supabase — база для текстов и прогресса
1. [supabase.com](https://supabase.com) → **Start your project** → зарегистрируйся личной почтой.
2. **New project**: имя `lector`, регион **Central EU (Frankfurt)**, пароль базы — сгенерируй и сохрани
   в менеджер паролей (приложению он не нужен). Тариф Free.
3. **SQL Editor** (иконка `>_` слева; [прямая ссылка](https://supabase.com/dashboard/project/_/sql/new)) → **New query** → вставь всё содержимое файла `supabase/schema.sql` → **Run**.
   Должно быть «Success. No rows returned».
4. **Authentication → URL Configuration**
   ([прямая ссылка](https://supabase.com/dashboard/project/_/auth/url-configuration)):
   - Site URL: `https://yacheater.github.io/spanishbookreader/`
   - Redirect URLs → Add: тот же адрес и `http://localhost:8765/**`
5. **Project Settings → API Keys** (новые ключи или вкладка Legacy — подходят оба вида)
   ([прямая ссылка](https://supabase.com/dashboard/project/_/settings/api-keys)):
   - `Project URL` и ключ **publishable** (`sb_publishable_…`; в Legacy он называется anon) — можно прислать мне в чат (они публичные по замыслу, защищает
     их правило доступа из `schema.sql`), я впишу в `app/config.js`;
   - **secret** ключ (`sb_secret_…`; в Legacy — service_role) — **не присылай в чат**. Файл `.env` уже лежит в папке Spanish (он скрытый — имя с точкой, Finder его
     не показывает; открыть: `open -e "/Users/nastya.andreeva/for Personal/Spanish/.env"`) — впиши ключ туда. Этот ключ даёт полный доступ к базе; `.env` в git не попадает.

Шаблон письма менять не нужно (Supabase требует для этого свой почтовый сервер): вход в приложение —
по почте и паролю.

## 2. GitHub — сайт приложения
1. Личный аккаунт на [github.com](https://github.com) (если нет).
2. **New repository** → имя `spanishbookreader`, **Public**, без README → Create.
3. Pages включает Claude (публикация из ветки `gh-pages`, туда попадает только папка `app/`).
4. Почта для коммитов: **Settings → Emails** → включи «Keep my email addresses private» и скопируй адрес
   вида `12345+login@users.noreply.github.com`. Пришли мне логин и этот адрес.
5. Вход для отправки кода — в терминале выполни сама и пройди вход в браузере **личным** аккаунтом:
   ```bash
   gh auth login --hostname github.com --git-protocol https --web
   ```
   (если `gh` нет: `brew install gh`). После этого я отправлю код, и через 1–2 минуты сайт откроется
   по адресу из шага 1.4.

## 3. Первый вход и загрузка текстов
1. Открой сайт → почта + придумай пароль → **Create account** → в письме нажми ссылку подтверждения
   (в любом браузере) → вернись и нажми **Sign in**.
2. Скажи мне — я выполню `python3 tools/publish_texts.py`: тексты загрузятся в твою закрытую таблицу
   и появятся в приложении.
3. **Authentication → Sign In / Providers** → выключи **Allow new users to sign up** — чтобы никто другой
   не смог завести аккаунт в твоём приложении.

## 4. Телефон
- iPhone: открой сайт в Safari → «Поделиться» → **«На экран Домой»**.
- Android: Chrome → ⋮ → **«Добавить на главный экран»**.
- Вход: почта и пароль. Прогресс синхронизируется сам: при каждом изменении и при
  возвращении в приложение. Статус — в шапке (synced / saving… / offline).

## Если что-то пошло не так
- «sync error» в шапке — открой Aa → **Sync now**; если не помогает, проверь интернет и что в Supabase
  выполнен `schema.sql`.
- Новые тексты: после обработки в Claude Code нужен ещё `python3 tools/publish_texts.py` — Claude делает это сам.
