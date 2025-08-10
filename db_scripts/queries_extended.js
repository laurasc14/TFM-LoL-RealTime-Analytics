const dbLol = db.getSiblingDB("lol");

// 1️⃣ Top 5 campeones por KDA medio
print("🏆 Top 5 Campeones por KDA medio:");
printjson(
  dbLol.matches_processed.aggregate([
    { $unwind: "$participants" },
    { $group: { _id: "$participants.championName", avgKDA: { $avg: "$participants.kda" } } },
    { $sort: { avgKDA: -1 } },
    { $limit: 5 }
  ]).toArray()
);

// 2️⃣ Top 5 Invocadores por Winrate
print("\n🔥 Top 5 Invocadores por Winrate:");
printjson(
  dbLol.matches_processed.aggregate([
    { $unwind: "$participants" },
    {
      $group: {
        _id: "$participants.summonerName",
        wins: { $sum: { $cond: ["$participants.win", 1, 0] } },
        total: { $sum: 1 }
      }
    },
    { $addFields: { winrate: { $multiply: [{ $divide: ["$wins", "$total"] }, 100] } } },
    { $sort: { winrate: -1, total: -1 } },
    { $limit: 5 }
  ]).toArray()
);

// 3️⃣ Histograma de duración de partidas (en minutos)
print("\n⏱ Histograma de duración de partidas (min):");
printjson(
  dbLol.matches_processed.aggregate([
    { $project: { durationMin: { $round: [{ $divide: ["$gameDuration", 60] }, 0] } } },
    { $group: { _id: "$durationMin", count: { $sum: 1 } } },
    { $sort: { _id: 1 } }
  ]).toArray()
);
