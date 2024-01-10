#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <time.h>
#include "secrets.h"
#include "readings.h"
#include <WiFiUdp.h>
#include <NTPClient.h>

/* ESP */
const int sensorIn = A0;	   // pin where the OUT pin from sensor is connected on Arduino
float resolution = 3.3 / 1024; // Input Voltage Range is 1V to 3.3V

/* ACS712 Sensor */
const double error = 0.035;
int mVperAmp = 100; // 100 for 20A Module

/* Current and Power */
int Watt = 0;
double Voltage = 0;
double VRMS = 0;
double AmpsRMS = 0;

// The MQTT topics that this device should publish/subscribe
#define AWS_IOT_PUBLISH_TOPIC "device_energy/pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "device_energy/sub"
#define GMT_OFFSET 3

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, GMT_OFFSET*3600);

/* WiFi */
WiFiClientSecure net;
// Configure WiFiClientSecure to use the AWS IoT device credentials
BearSSL::X509List client_cert(AWS_CERT_CRT);
BearSSL::PrivateKey key(AWS_CERT_PRIVATE);
BearSSL::X509List cert(AWS_CERT_CA);

PubSubClient client(net);

time_t now;
time_t nowish = 1510592825;
unsigned long lastMillis = 0;

/* Function Declarations*/
float getVPP();
void NTPConnect(void);
void messageHandler(char *topic, byte *payload, unsigned int length);
void connectAWS();
void publishMessage(reading power);
reading get_readings();

void setup()
{
	Serial.begin(9600);
	pinMode(sensorIn, INPUT);
	connectAWS();
	// WiFi.mode(WIFI_OFF)
	wifi_set_sleep_type(NONE_SLEEP_T);
	timeClient.begin();
}

void loop()
{
	reading r = get_readings();
	timeClient.update();
	Serial.print(r.Irms, 4);
	Serial.print("A  ---  ");
	Serial.print(r.watts);
	Serial.println(" W");
	delay(100);

	now = time(nullptr);

	if (!client.connected())
	{
		connectAWS();
	}
	else
	{
		client.loop();
		publishMessage(r);
	}
}

void NTPConnect(void)
{
	Serial.print("Setting time using SNTP");
	configTime(GMT_OFFSET * 3600, 0 * 3600, "pool.ntp.org", "time.nist.gov");
	now = time(nullptr);
	while (now < nowish)
	{
		delay(500);
		Serial.print(".");
		now = time(nullptr);
	}
	Serial.println("done!");
	struct tm timeinfo;
	gmtime_r(&now, &timeinfo);
	Serial.print("Current time: ");
	Serial.print(asctime(&timeinfo));
}

void connectAWS()
{
	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

	Serial.println("Connecting to Wi-Fi" + String(WIFI_SSID));

	while (WiFi.status() != WL_CONNECTED)
	{
		delay(500);
		Serial.println("trying wifi...");
	}

	NTPConnect();

	net.setTrustAnchors(&cert);
	net.setClientRSACert(&client_cert, &key);

	// Connect to the MQTT broker on the AWS endpoint we defined earlier
	client.setServer(AWS_IOT_ENDPOINT, 8883).setCallback(messageHandler);

	Serial.println("Connecting to AWS IOT");

	while (!client.connect(THINGNAME))
	{
		Serial.println("trying aws IoT...");
		Serial.print(client.state());
		delay(500);
	}

	if (!client.connected())
	{
		Serial.println("AWS IoT Timeout!");
		return;
	}

	// Subscribe to a topic
	client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC);

	Serial.println("AWS IoT Connected!");
}

void publishMessage(reading r)
{
	StaticJsonDocument<200> doc;
	doc["time"] = r.time;
	doc["rms_current"] = r.Irms;
	doc["power"] = r.watts;
	char jsonBuffer[512];
	serializeJson(doc, jsonBuffer); // print to client

	client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
}

void messageHandler(char *topic, byte *payload, unsigned int length)
{
	Serial.print("incoming: ");
	Serial.println(topic);

	StaticJsonDocument<200> doc;
	deserializeJson(doc, payload);
	const char *message = doc["message"];
	Serial.println(message);
}

float getVPP()
{
	float result;
	int readValue;		 // value read from the sensor
	int maxValue = 0;	 // store max value here
	int minValue = 1024; // store min value here ESP ADC resolution

	uint32_t start_time = millis();
	while ((millis() - start_time) < 1000) // sample for 1 Sec
	{
		readValue = analogRead(sensorIn);
		// see if you have a new maxValue
		if (readValue > maxValue)
		{
			/*record the maximum sensor value*/
			maxValue = readValue;
		}
		if (readValue < minValue)
		{
			/*record the minimum sensor value*/
			minValue = readValue;
		}
		delay(5);
	}

	// Subtract min from max
	result = (maxValue - minValue) * resolution;

	return result;
}

reading get_readings()
{
	reading read;

	Voltage = getVPP();
	VRMS = (Voltage / 2.0) * 0.707;
	AmpsRMS = ((VRMS * 1000) / mVperAmp) - error;
	Watt = (AmpsRMS * 240);

	time_t epochTime = timeClient.getEpochTime();
	
	read.time = epochTime;
	read.Irms = AmpsRMS;
	read.watts = Watt;

	return read;
}
