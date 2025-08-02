#!/bin/bash
echo "Insertando datos de prueba realistas en MongoDB..."
docker exec -i final-mongo mongo <<EOF
use league

db.champions.insertMany([
  { championId: 103, name: "Ahri", role: "Mage", winRate: 51.2 },
  { championId: 64, name: "Lee Sin", role: "Jungler", winRate: 48.9 },
  { championId: 222, name: "Jinx", role: "ADC", winRate: 52.1 }
])

db.matches.insertMany([
  {
    matchId: "NA1_1234567890",
    duration: 1820,
    winner: "Blue",
    teams: {
      blue: { kills: 25, deaths: 20, gold: 56000 },
      red: { kills: 20, deaths: 25, gold: 51000 }
    },
    participants: [
      { summonerName: "Player1", champion: "Ahri", kills: 10, deaths: 3, assists: 8 },
      { summonerName: "Player2", champion: "Lee Sin", kills: 5, deaths: 6, assists: 10 },
      { summonerName: "Player3", champion: "Jinx", kills: 7, deaths: 4, assists: 9 }
    ]
  },
  {
    matchId: "EUW1_0987654321",
    duration: 2100,
    winner: "Red",
    teams: {
      blue: { kills: 18, deaths: 30, gold: 48000 },
      red: { kills: 30, deaths: 18, gold: 59000 }
    },
    participants: [
      { summonerName: "PlayerA", champion: "Jinx", kills: 12, deaths: 5, assists: 6 },
      { summonerName: "PlayerB", champion: "Ahri", kills: 6, deaths: 8, assists: 11 },
      { summonerName: "PlayerC", champion: "Lee Sin", kills: 9, deaths: 4, assists: 12 }
    ]
  }
])
EOF
echo "Datos insertados correctamente."
