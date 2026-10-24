/* Lector sync — merges progress between devices through Supabase.
   Pure merge logic (works in node for tests) + a thin Supabase adapter used by app.js.

   Model: every item of the synced collections has a change time in state.stamps["<coll>:<key>"];
   deletions leave a tombstone in state.deleted["<coll>:<key>"]. Stamps are set automatically by
   Sync.stamp() on every save by diffing against the last snapshot, so app code never has to.
   Merge = per item, newest event wins (edit on one device, delete on another → whichever is later). */
"use strict";

const SYNCED = ["cards", "folders", "known", "positions"];

const Sync = {
  snapshot: {},

  /** Call once after loading local state: remembers items as they are, stamps unstamped ones. */
  init(state, now = Date.now()) {
    state.stamps = state.stamps || {};
    state.deleted = state.deleted || {};
    this.snapshot = {};
    for (const coll of SYNCED) {
      for (const [k, v] of Object.entries(state[coll] || {})) {
        const id = coll + ":" + k;
        this.snapshot[id] = JSON.stringify(v);
        if (!state.stamps[id]) state.stamps[id] = (v && v.added) || now;
      }
    }
  },

  /** Call on every save: stamps changed items, records deletions. Returns true if anything changed. */
  stamp(state, now = Date.now()) {
    let changed = false;
    const seen = new Set();
    for (const coll of SYNCED) {
      for (const [k, v] of Object.entries(state[coll] || {})) {
        const id = coll + ":" + k, j = JSON.stringify(v);
        seen.add(id);
        if (this.snapshot[id] !== j) {
          this.snapshot[id] = j; state.stamps[id] = now; delete state.deleted[id]; changed = true;
        }
      }
    }
    for (const id of Object.keys(this.snapshot)) {
      if (!seen.has(id)) { delete this.snapshot[id]; delete state.stamps[id]; state.deleted[id] = now; changed = true; }
    }
    return changed;
  },

  /** The part of the state that travels between devices. */
  payload(state) {
    const p = { stamps: state.stamps, deleted: state.deleted, v: 1 };
    for (const coll of SYNCED) p[coll] = state[coll] || {};
    return p;
  },

  /** Merge remote payload into local state (in place). Returns true if local state changed. */
  merge(state, remote) {
    if (!remote) return false;
    const rs = remote.stamps || {}, rd = remote.deleted || {};
    let changed = false;
    for (const coll of SYNCED) {
      const L = state[coll] = state[coll] || {}, R = remote[coll] || {};
      const keys = new Set([...Object.keys(L), ...Object.keys(R)]);
      for (const id of Object.keys(rd)) if (id.startsWith(coll + ":")) keys.add(id.slice(coll.length + 1));
      for (const id of Object.keys(state.deleted)) if (id.startsWith(coll + ":")) keys.add(id.slice(coll.length + 1));
      for (const k of keys) {
        const id = coll + ":" + k;
        const lt = k in L ? state.stamps[id] || 0 : 0, rt = k in R ? rs[id] || 0 : 0;
        const del = Math.max(state.deleted[id] || 0, rd[id] || 0);
        if (del && del >= lt && del >= rt) {                 // deletion is the newest event
          if (k in L) { delete L[k]; changed = true; }
          delete state.stamps[id]; state.deleted[id] = del;
          delete this.snapshot[id];
        } else if (rt > lt) {                                 // remote edit is newer
          L[k] = R[k]; state.stamps[id] = rt; delete state.deleted[id];
          this.snapshot[id] = JSON.stringify(R[k]); changed = true;
        }
      }
    }
    // tombstones 60 days older than the newest change are forgotten
    const newest = Math.max(0, ...Object.values(state.stamps), ...Object.values(state.deleted));
    const cutoff = newest - 60 * 864e5;
    for (const [id, t] of Object.entries(state.deleted)) if (t < cutoff) delete state.deleted[id];
    return changed;
  },
};

/* ---------- Supabase adapter (browser only) ---------- */
const Cloud = {
  client: null, user: null, status: "local", onStatus: null, onRemoteChange: null,
  timer: null, busy: false, again: false,

  enabled() {
    const c = window.LECTOR_CONFIG || {};
    return !!(c.supabaseUrl && c.supabaseAnonKey && window.supabase && location.protocol.startsWith("http"));
  },
  setStatus(s) { this.status = s; if (this.onStatus) this.onStatus(s); },

  async start() {
    if (!this.enabled()) { this.setStatus("local"); return false; }
    const c = window.LECTOR_CONFIG;
    this.client = window.supabase.createClient(c.supabaseUrl, c.supabaseAnonKey,
      { auth: { flowType: "implicit", detectSessionInUrl: true, persistSession: true } });
    const { data } = await this.client.auth.getSession();
    this.user = data.session ? data.session.user : null;
    if (/access_token|error_description/.test(location.hash)) history.replaceState(null, "", location.pathname + "#/");
    this.client.auth.onAuthStateChange((_e, session) => {
      const was = this.user && this.user.id;
      this.user = session ? session.user : null;
      if ((this.user && this.user.id) !== was) location.reload();
    });
    this.setStatus(this.user ? "idle" : "signed-out");
    return true;
  },

  async sendLink(email) {
    return this.client.auth.signInWithOtp({ email, options: { emailRedirectTo: location.origin + location.pathname, shouldCreateUser: true } });
  },
  async signInPassword(email, password) { return this.client.auth.signInWithPassword({ email, password }); },
  async signUp(email, password) {
    return this.client.auth.signUp({ email, password, options: { emailRedirectTo: location.origin + location.pathname } });
  },
  async signOut() { await this.client.auth.signOut(); },

  /** Pull remote, merge into local, push the result. Safe to call often. */
  async sync(state, save) {
    if (!this.user) return;
    if (this.busy) { this.again = true; return; }
    this.busy = true; this.setStatus("syncing");
    try {
      const { data, error } = await this.client.from("progress").select("state").eq("user_id", this.user.id).maybeSingle();
      if (error) throw error;
      const changed = Sync.merge(state, data && data.state);
      if (changed) { save(true); if (this.onRemoteChange) this.onRemoteChange(); }
      const body = Sync.payload(state);
      if (!data || JSON.stringify(data.state) !== JSON.stringify(body)) {
        const { error: e2 } = await this.client.from("progress").upsert({ user_id: this.user.id, state: body, updated_at: new Date().toISOString() });
        if (e2) throw e2;
      }
      this.setStatus("synced");
    } catch (e) {
      console.warn("sync failed", e);
      this.setStatus(navigator.onLine === false ? "offline" : "error");
    } finally {
      this.busy = false;
      if (this.again) { this.again = false; this.sync(state, save); }
    }
  },
  schedule(state, save) {
    if (!this.user) return;
    clearTimeout(this.timer);
    this.setStatus("pending");
    this.timer = setTimeout(() => this.sync(state, save), 1500);
  },

  async listTexts() {
    const { data, error } = await this.client.from("texts").select("id,title,meta,updated_at").order("updated_at", { ascending: false });
    if (error) throw error;
    return data.map((r) => ({ id: r.id, title: r.title, ...(r.meta || {}) }));
  },
  async suggest(row) {
    const { error } = await this.client.from("submissions").insert(row);
    return error;
  },
  async mySuggestions() {
    const { data, error } = await this.client.from("submissions").select("id,title,source_url,status,reply,created_at")
      .order("created_at", { ascending: false }).limit(20);
    return error ? [] : data;
  },
  async loadText(id) {
    const { data, error } = await this.client.from("texts").select("data").eq("id", id).maybeSingle();
    if (error) throw error;
    return data && data.data;
  },
};

if (typeof module !== "undefined") module.exports = { Sync, SYNCED };
