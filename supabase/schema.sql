-- Lector — Supabase schema. Paste into Supabase → SQL Editor → Run (safe to run again).
-- Two tables, both private to their owner through row-level security:
--   texts    — processed texts (uploaded by tools/publish_texts.py with the service key)
--   progress — one row per user with the synced learning state (written by the app)

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

drop policy if exists "read own texts" on public.texts;
create policy "read own texts" on public.texts
  for select using (owner = auth.uid());

drop policy if exists "own progress" on public.progress;
create policy "own progress" on public.progress
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
