-- Lector — Supabase schema. Paste into Supabase → SQL Editor → Run (safe to run again).
-- Full current schema (= 001 + migrations/002…). Existing projects: run only the newer files in migrations/.
--   texts       — processed texts (uploaded by tools/publish_texts.py), visible to owner + readers
--   progress    — one row per user with the synced learning state (written by the app)
--   submissions — "Suggest a text" queue (written by the app, processed by tools/suggestions.py)

create table if not exists public.texts (
  id         text primary key,
  owner      uuid not null references auth.users (id) on delete cascade,
  title      text not null,
  meta       jsonb not null default '{}'::jsonb,   -- source, words, chapters (for the library list)
  data       jsonb not null,                        -- the full texts/<id>.json
  updated_at timestamptz not null default now()
);

create table if not exists public.progress (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  state      jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.texts    enable row level security;
alter table public.progress enable row level security;


drop policy if exists "own progress" on public.progress;
create policy "own progress" on public.progress
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 1. Sharing: a text is visible to its owner and to everyone in `readers`.
alter table public.texts add column if not exists readers uuid[] not null default '{}';

drop policy if exists "read own texts" on public.texts;
drop policy if exists "read own or shared texts" on public.texts;
create policy "read own or shared texts" on public.texts
  for select using (owner = auth.uid() or auth.uid() = any (readers));

-- 2. Queue: any signed-in user can suggest a text; they see only their own suggestions.
--    Claude picks them up with tools/suggestions.py (service key) and marks them processed.
create table if not exists public.submissions (
  id           bigint generated always as identity primary key,
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title        text not null default '',
  source_url   text not null default '',
  body         text not null default '',
  note         text not null default '',
  status       text not null default 'new' check (status in ('new', 'processing', 'done', 'rejected')),
  text_id      text,
  reply        text not null default '',
  created_at   timestamptz not null default now(),
  processed_at timestamptz
);
alter table public.submissions enable row level security;

drop policy if exists "suggest texts" on public.submissions;
create policy "suggest texts" on public.submissions
  for insert with check (user_id = auth.uid() and status = 'new');

drop policy if exists "see own suggestions" on public.submissions;
create policy "see own suggestions" on public.submissions
  for select using (user_id = auth.uid());
drop policy if exists "delete own texts" on public.texts;
create policy "delete own texts" on public.texts
  for delete using (owner = auth.uid());
