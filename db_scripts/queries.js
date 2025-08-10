// queries.js
const dbLol = db.getSiblingDB("lol");

// 1) KDA medio por partida
printjson(
  dbLol.matches_processed.aggregate([
    { $unwind: "$participants" },
    { $group: { _id: "$match_id", avgKDA: { $avg: "$participants.kda" } } },
    { $sort: { _id: -1 } },
    { $limit: 3 }
  ]).toArray()
);

// 2) Top-5 KDAs
printjson(
  dbLol.matches_processed.aggregate([
    { $unwind: "$participants" },
    { $project: { name: "$participants.summonerName", kda: "$participants.kda" } },
    { $sort: { kda: -1 } },
    { $limit: 5 }
  ]).toArray()
);
