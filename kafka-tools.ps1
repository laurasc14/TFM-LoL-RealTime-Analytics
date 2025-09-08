# =========================
# Config
# =========================
$Global:KafkaService = "final-kafka"
$Global:Broker       = "localhost:9092"
$Global:TopicRaw     = "lol.raw"
$Global:TopicOut     = "lol.expanded"

# =========================
# Enviar una lista de objetos (hashtables) como JSON Lines al topic raw
# Uso:
#   Send-KafkaJson @(
#     @{ match_id = 9101; msg = "ok-9101" },
#     @{ match_id = 9102; msg = "ok-9102" }
#   )
# =========================
function Send-KafkaJson {
    param(
        [Parameter(Mandatory)]
        [Array] $Objects,

        [string] $Topic = $Global:TopicRaw,
        [string] $Service = $Global:KafkaService,
        [string] $BrokerStr = $Global:Broker
    )

    # 1) Serializa cada objeto como una línea JSON
    $jsonl = ($Objects | ForEach-Object { $_ | ConvertTo-Json -Compress }) -join "`n"

    # 2) Pipea el contenido al contenedor y prodúcelo
    $cmd = @"
cat > /tmp/payloads.jsonl
kafka-console-producer --bootstrap-server $BrokerStr --topic $Topic < /tmp/payloads.jsonl
"@

    $jsonl | docker compose exec -T $Service bash -lc $cmd
}

# =========================
# Consumir del topic de salida con un group.id efímero
# Uso:
#   Receive-KafkaExpanded -TimeoutMs 15000
# =========================
function Receive-KafkaExpanded {
    param(
        [int] $TimeoutMs = 15000,
        [string] $Topic = $Global:TopicOut,
        [string] $Service = $Global:KafkaService,
        [string] $BrokerStr = $Global:Broker
    )

    $epoch = [int][double]::Parse((Get-Date -UFormat %s))
    $gid = "verify-$epoch"

    docker compose exec $Service bash -lc `
      "kafka-console-consumer --bootstrap-server $BrokerStr --topic $Topic --from-beginning --timeout-ms $TimeoutMs --consumer-property group.id=$gid"
}

# =========================
# (Opcional) Resetear offsets del consumer del servicio al final
# Uso:
#   Reset-MatchExpanderOffsets
# =========================
function Reset-MatchExpanderOffsets {
    param(
        [string] $Service = $Global:KafkaService,
        [string] $BrokerStr = $Global:Broker,
        [string] $Topic = $Global:TopicRaw,
        [string] $Group = "match-expander"
    )
    docker compose exec $Service bash -lc `
      "kafka-consumer-groups --bootstrap-server $BrokerStr --group $Group --topic $Topic --reset-offsets --to-latest --execute"
}
