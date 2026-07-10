/*
 * Tinkle :: Poop Deck telemetry publisher
 *
 * Fire-and-forget. Publishing NEVER blocks or gates irrigation control.
 * If the broker is down, the event is dropped and the valve still closes.
 *
 * Libraries: PubSubClient, ArduinoJson
 *
 * Fold into your existing loop. Call publishRun() at each zone's close,
 * not once per cycle.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

static const char* MQTT_HOST   = "192.168.1.xxx";  // Beelink
static const uint16_t MQTT_PORT = 1883;
static const char* MQTT_CLIENT_ID = "tinkle";
static const uint8_t SCHEMA_V = 1;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

// Non-blocking reconnect. Called from loop(), never spins.
static unsigned long lastMqttAttempt = 0;
static const unsigned long MQTT_RETRY_MS = 30000;

void mqttTick() {
  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }
  unsigned long now = millis();
  if (now - lastMqttAttempt < MQTT_RETRY_MS) return;
  lastMqttAttempt = now;
  mqtt.connect(MQTT_CLIENT_ID);   // don't care if it fails; we retry
}

void mqttBegin() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(384);
  // NTP: we publish UTC. Local time is a display concern, not a storage one.
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

// Format an epoch (UTC seconds) as ISO-8601 with trailing Z.
static void isoUtc(time_t t, char* out, size_t n) {
  struct tm tmv;
  gmtime_r(&t, &tmv);
  strftime(out, n, "%Y-%m-%dT%H:%M:%SZ", &tmv);
}

/*
 * Call at zone close.
 *   zone       : 1..3
 *   startEpoch : UTC epoch seconds when the zone opened
 *   durationS  : elapsed seconds the valve was open
 *   gallons    : totalized for THIS zone (NAN if unmetered)
 *   fertigated : true only on the first run of the day
 *   trigger    : "scheduled" | "manual"
 *   fault      : nullptr when clean, else a short code
 *
 * Returns false if the event didn't make it to the broker. Callers should
 * ignore the return value for control purposes -- it's telemetry, not gospel.
 */
bool publishRun(uint8_t zone, time_t startEpoch, uint32_t durationS,
                float gallons, bool fertigated, const char* trigger,
                const char* fault) {

  if (!mqtt.connected()) return false;   // drop it, keep irrigating

  char ts[24];
  isoUtc(startEpoch, ts, sizeof(ts));

  JsonDocument doc;
  doc["v"]          = SCHEMA_V;
  doc["source"]     = MQTT_CLIENT_ID;
  doc["zone"]       = zone;
  doc["ts_start"]   = ts;
  doc["duration_s"] = durationS;

  if (isnan(gallons)) doc["gallons"] = nullptr;
  else                doc["gallons"] = serialized(String(gallons, 2));

  doc["fertigated"] = fertigated;
  doc["trigger"]    = trigger;

  if (fault) doc["fault"] = fault;
  else       doc["fault"] = nullptr;

  char payload[384];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  char topic[48];
  snprintf(topic, sizeof(topic), "farm/irrigation/tinkle/zone%u", zone);

  // QoS 0, retain false. The DB has a unique key, so a redelivery would be
  // harmless -- but PubSubClient is QoS 0 on publish anyway. Losing one event
  // to a down broker is acceptable; losing a run to a blocked publish is not.
  return mqtt.publish(topic, (const uint8_t*)payload, len, false);
}

/*
 * Backfill note:
 * You already keep runs in local memory. Add a small ring buffer of the last
 * N unpublished events; on reconnect, drain it. The unique index on
 * (source, zone, ts_start) makes replay idempotent -- late events land in the
 * right place in history, duplicates are silently ignored.
 */
