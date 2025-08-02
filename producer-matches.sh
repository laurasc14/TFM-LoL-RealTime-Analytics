#!/bin/bash
echo "Enviando datos simulados de partidas al topic 'matches'..."
docker exec -i kafka1 kafka-console-producer.sh \
  --broker-list kafka1:9092 \
  --topic matches <<EOF
{"matchId": "NA1_1234567890", "winner": "Blue", "duration": 1820, "participants": [{"summonerName": "Player1", "champion": "Ahri", "kills": 10, "deaths": 3, "assists": 8}, {"summonerName": "Player2", "champion": "Lee Sin", "kills": 5, "deaths": 6, "assists": 10}, {"summonerName": "Player3", "champion": "Jinx", "kills": 7, "deaths": 4, "assists": 9}]}
{"matchId": "EUW1_0987654321", "winner": "Red", "duration": 2100, "participants": [{"summonerName": "PlayerA", "champion": "Jinx", "kills": 12, "deaths": 5, "assists": 6}, {"summonerName": "PlayerB", "champion": "Ahri", "kills": 6, "deaths": 8, "assists": 11}, {"summonerName": "PlayerC", "champion": "Lee Sin", "kills": 9, "deaths": 4, "assists": 12}]}
EOF
echo "Datos enviados correctamente."
