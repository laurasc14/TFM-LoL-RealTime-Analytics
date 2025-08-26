db = db.getSiblingDB('lol');
db.createUser({
  user: 'appuser',
  pwd: 'appsecret',
  roles: [{ role: 'readWrite', db: 'lol' }]
});
