// Tests the device-to-device merge in app/sync.js with two simulated devices and a fake server.
// Run: node tools/test_sync.js
"use strict";
const { Sync } = require("../app/sync.js");

let fails = 0;
const ok = (cond, msg) => { if (!cond) { fails++; console.log("FAIL", msg); } else console.log("ok  ", msg); };
const clone = (x) => JSON.parse(JSON.stringify(x));

// Each device has its own Sync snapshot; emulate by swapping snapshots around calls.
function device(state) {
  const d = { state, snap: {} };
  const prev = Sync.snapshot; Sync.init(state, 1000); d.snap = Sync.snapshot; Sync.snapshot = prev;
  d.save = (now) => { const p = Sync.snapshot; Sync.snapshot = d.snap; Sync.stamp(d.state, now); d.snap = Sync.snapshot; Sync.snapshot = p; };
  d.sync = (server) => {        // pull, merge, push — what Cloud.sync does
    const p = Sync.snapshot; Sync.snapshot = d.snap;
    Sync.merge(d.state, server.state && clone(server.state));
    server.state = clone(Sync.payload(d.state));
    d.snap = Sync.snapshot; Sync.snapshot = p;
  };
  return d;
}
const card = (key, extra = {}) => ({ key, added: 500, srs: { reps: 0 }, folders: ["t:mate"], ...extra });
const server = { state: null };

// laptop has progress, phone is new
const laptop = device({ cards: { "tomar.v": card("tomar.v"), "hoja.n": card("hoja.n") }, folders: { "t:mate": { id: "t:mate", name: "Mate" } }, known: {}, positions: {} });
const phone = device({ cards: {}, folders: {}, known: {}, positions: {} });
laptop.sync(server); phone.sync(server);
ok(Object.keys(phone.state.cards).length === 2, "phone receives laptop's cards on first sync");

// phone learns a word (test passed), laptop adds a new word — offline at the same time
phone.state.cards["tomar.v"].srs.reps = 1; phone.save(2000);
laptop.state.cards["yerba.n"] = card("yerba.n", { added: 2100 }); laptop.save(2100);
phone.sync(server); laptop.sync(server); phone.sync(server);
ok(laptop.state.cards["tomar.v"].srs.reps === 1, "laptop gets phone's test result");
ok(!!phone.state.cards["yerba.n"], "phone gets laptop's new word");
ok(Object.keys(laptop.state.cards).length === 3 && Object.keys(phone.state.cards).length === 3, "both have 3 cards");

// laptop deletes a word, phone edits another one later
delete laptop.state.cards["hoja.n"]; laptop.save(3000);
phone.state.cards["yerba.n"].folders.push("u:1"); phone.save(3100);
laptop.sync(server); phone.sync(server); laptop.sync(server);
ok(!phone.state.cards["hoja.n"] && !laptop.state.cards["hoja.n"], "deletion reaches the other device");
ok(laptop.state.cards["yerba.n"].folders.includes("u:1"), "later edit on phone survives");

// conflict: both edit the same word — the later change wins
laptop.state.cards["tomar.v"].srs.reps = 5; laptop.save(4000);
phone.state.cards["tomar.v"].srs.reps = 0; phone.save(4100);
laptop.sync(server); phone.sync(server); laptop.sync(server);
ok(laptop.state.cards["tomar.v"].srs.reps === 0 && phone.state.cards["tomar.v"].srs.reps === 0, "same word edited on both: newest wins");

// delete on one device vs older edit on the other: delete wins; re-adding later brings it back
phone.state.cards["yerba.n"].srs.reps = 2; phone.save(5000);
delete laptop.state.cards["yerba.n"]; laptop.save(5100);
phone.sync(server); laptop.sync(server); phone.sync(server);
ok(!phone.state.cards["yerba.n"], "newer delete beats older edit");
phone.state.cards["yerba.n"] = card("yerba.n", { added: 6000 }); phone.save(6000);
phone.sync(server); laptop.sync(server);
ok(!!laptop.state.cards["yerba.n"], "word re-added after delete comes back");

// known words and reading positions travel too; unchanged saves don't create changes
laptop.state.known["de.prep"] = 7000; laptop.state.positions.mate = 0.4; laptop.save(7000);
laptop.sync(server); phone.sync(server);
ok(phone.state.known["de.prep"] && phone.state.positions.mate === 0.4, "known words and reading position sync");
const before = JSON.stringify(server.state);
phone.save(8000); phone.sync(server);
ok(JSON.stringify(server.state) === before, "a save without changes changes nothing");

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
