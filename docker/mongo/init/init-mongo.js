db = db.getSiblingDB("lol_realtime");

// Matches
db.createCollection("matches", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["match_id", "timestamp"],
      properties: {
        match_id: { bsonType: "int" },
        team: { bsonType: "string" },
        result: { bsonType: "string" },
        timestamp: { bsonType: "date" }
      }
    }
  }
});

// Players
db.createCollection("players", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["player_id", "name"],
      properties: {
        player_id: { bsonType: "int" },
        name: { bsonType: "string" },
        role: { bsonType: "string" }
      }
    }
  }
});

// Events
db.createCollection("events", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["event_id", "match_id", "timestamp"],
      properties: {
        event_id: { bsonType: "int" },
        match_id: { bsonType: "int" },
        type: { bsonType: "string" },
        description: { bsonType: "string" },
        timestamp: { bsonType: "date" }
      }
    }
  }
});
