// init-mongo.js
// Crea el usuario de la app en la DB correcta y mete un documento de salud.
const dbName = 'lol_realtime';
const appUser = 'app';
const appPass = 'appsecret';

let db = db.getSiblingDB(dbName);

db.createUser({
  user: appUser,
  pwd: appPass,
  roles: [{ role: 'readWrite', db: dbName }],
});

db.health.insertOne({ ok: true, when: new Date() });
