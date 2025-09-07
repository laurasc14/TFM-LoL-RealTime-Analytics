db = db.getSiblingDB('lol_realtime');

db.createUser({
    user: "app",
    pwd: "appsecret",
    roles: [
        { role: "readWrite", db: "lol_realtime" }
    ]
});