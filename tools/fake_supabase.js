// In-memory stand-in for supabase-js used by tools/cloud_test.html (only the calls app/sync.js makes).
// Data and session live in sessionStorage so they survive the reload the app does after sign-in.
(function () {
  const load = (k, d) => { try { return JSON.parse(sessionStorage.getItem(k)) || d; } catch (e) { return d; } };
  const FAKE = window.FAKE = {
    db: load("fake_db", { texts: [], progress: [], submissions: [] }),
    session: load("fake_session", null), listeners: [], calls: [],
    persist() { sessionStorage.setItem("fake_db", JSON.stringify(this.db)); sessionStorage.setItem("fake_session", JSON.stringify(this.session)); },
  };
  const copy = (x) => JSON.parse(JSON.stringify(x));      // a real server never shares objects with the page
  const pick = (row, cols) => copy(cols === "*" ? row : Object.fromEntries(cols.split(",").map((c) => [c, row[c]])));
  function query(table) {
    const q = { cols: "*", filters: [] };
    FAKE.db[table] = FAKE.db[table] || [];
    const visible = (r) => table !== "texts" || r.owner === (FAKE.session && FAKE.session.user.id) || r.public;   // RLS
    const rows = () => FAKE.db[table].filter((r) => visible(r) && q.filters.every(([c, v]) => r[c] === v)).map((r) => pick(r, q.cols));
    Object.assign(q, {
      select(cols) { q.cols = cols; FAKE.calls.push((q.del ? "delete " : "select ") + table); return q; },
      eq(c, v) { q.filters.push([c, v]); return q; },
      order() { return q; },
      limit() { return q; },
      delete() { q.del = true; return q; },
      insert(row) {
        FAKE.calls.push("insert " + table);
        FAKE.db[table].push({ id: FAKE.db[table].length + 1, user_id: FAKE.session.user.id, status: "new", reply: "",
          created_at: new Date().toISOString(), ...copy(row) });
        FAKE.persist(); return Promise.resolve({ error: null });
      },
      select_after_delete: null,
      maybeSingle() { return Promise.resolve({ data: rows()[0] || null, error: null }); },
      then(ok, bad) {
        const out = rows();
        if (q.del) {
          const mine = (r) => q.filters.every(([c, v]) => r[c] === v) && r.owner === FAKE.session.user.id;   // RLS: owner only
          const gone = FAKE.db[table].filter(mine).map((r) => pick(r, q.cols));
          FAKE.db[table] = FAKE.db[table].filter((r) => !mine(r)); FAKE.persist();
          return Promise.resolve({ data: gone, error: null }).then(ok, bad);
        }
        return Promise.resolve({ data: out, error: null }).then(ok, bad);
      },
      upsert(obj) {
        FAKE.calls.push("upsert " + table); obj = copy(obj);
        const key = table === "progress" ? "user_id" : "id";
        const i = FAKE.db[table].findIndex((r) => r[key] === obj[key]);
        if (i >= 0) FAKE.db[table][i] = obj; else FAKE.db[table].push(obj);
        FAKE.persist(); return Promise.resolve({ error: null });
      },
    });
    return q;
  }
  const client = {
    auth: {
      async getSession() { return { data: { session: FAKE.session } }; },
      onAuthStateChange(cb) { FAKE.listeners.push(cb); },
      async signInWithOtp({ email }) { FAKE.calls.push("otp " + email); return { error: null }; },
      async signUp({ email }) { FAKE.calls.push("signUp " + email); FAKE.db.confirmed = false; FAKE.db.user = email; FAKE.persist(); return { data: { session: null }, error: null }; },
      async signInWithPassword({ email, password }) {
        if (password !== "correct-horse") return { error: { message: "Invalid login credentials" } };
        if (FAKE.db.confirmed === false) return { error: { message: "Email not confirmed" } };
        FAKE.session = { user: { id: "u1", email } }; FAKE.persist();
        FAKE.listeners.forEach((cb) => cb("SIGNED_IN", FAKE.session)); return { error: null };
      },
      async signOut() { FAKE.session = null; FAKE.persist(); FAKE.listeners.forEach((cb) => cb("SIGNED_OUT", null)); },
    },
    from: query,
  };
  window.supabase = { createClient: () => client };
  window.LECTOR_CONFIG = { supabaseUrl: "https://fake.supabase.co", supabaseAnonKey: "fake" };
})();
