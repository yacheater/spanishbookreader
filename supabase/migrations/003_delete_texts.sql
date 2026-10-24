-- Lector migration 003 (2026-10-24): owners can delete their texts from the app (two-step confirm in the UI).
-- Readers of a shared text can't delete it — the app hides it from their library instead.
drop policy if exists "delete own texts" on public.texts;
create policy "delete own texts" on public.texts
  for delete using (owner = auth.uid());
