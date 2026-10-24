-- Lector migration 004 (2026-10-24): an open shelf — texts marked public are readable by every signed-in user.
alter table public.texts add column if not exists public boolean not null default false;
drop policy if exists "read public texts" on public.texts;
create policy "read public texts" on public.texts
  for select using (public and auth.uid() is not null);
