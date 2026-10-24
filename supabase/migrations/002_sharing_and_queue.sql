-- Lector migration 002 (2026-10-24): texts can be shared with other accounts; "Suggest a text" queue.
-- Paste into Supabase → SQL Editor → Run. Safe to run again.

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
