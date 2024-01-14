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
#define sensorIn A0	   // pin where the OUT pin from sensor is connected
float resolution = 3.3 / 1024; // Input Voltage Range is 1V to 3.3V

/* ACS712 Sensor */
const double error = 0.075; //wifi connected noise? + sensor at no load
int mVperAmp = 100; // 100 for 20A Module

/* Current and Power */
int Watt = 0;
double Voltage = 0;
double VRMS = 0;
double AmpsRMS = 0;

// The MQTT topics that this device should publish/subscribe
#define AWS_IOT_PUBLISH_TOPIC "device_energy/readings/acs_000"
#define AWS_IOT_SUBSCRIBE_TOPIC "device_energy/sub"
#define GMT_OFFSET 3

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, GMT_OFFSET * 3600);

/* WiFi */
WiFiClientSecure net;
// Configure WiFiClientSecure to use the AWS IoT device credentials
BearSSL::X509List client_cert(AWS_CERT_CRT);
BearSSL::PrivateKey key(AWS_CERT_PRIVATE);
BearSSL::X509List cert(AWS_CERT_CA);

PubSubClient client(net);

time_t now;
time_t nowish = 1705244380;
unsigned long lastMillis = 0;
float watt_hours = 0;
uint32_t period = 1000000 / 60; // One period of a 60Hz periodic waveform
uint32_t t_start = 0;
float zero_ADC_Value = 0;

/* Function Declarations*/
float getVPP();
void connect_wifi();
void NTPConnect(void);
void connectAWS();
bool publishReading(reading power);
reading get_readings();

void setup()
{
	Serial.begin(9600);
	pinMode(sensorIn, INPUT);
	connectAWS();
	// WiFi.mode(WIFI_OFF)
	wifi_set_sleep_type(NONE_SLEEP_T);
	timeClient.begin();

	t_start = micros();
	uint32_t ADC_SUM = 0, n = 0;
	while (micros() - t_start < period)
	{
		ADC_SUM += analogRead(sensorIn);
		n++;
	}
	zero_ADC_Value = ADC_SUM / n;
}

void loop()
{
	timeClient.update();
	reading r = get_readings();

	Serial.print(r.Irms, 6);
	Serial.println(" Amps");
	Serial.print(r.watts, 4);
	Serial.println(" Watts");
	Serial.print(r.watt_hours);
	Serial.println(" Wh");
	Serial.println("-----");

	if (!client.loop())
	{
		Serial.println("PubSub Client not connected " + client.state());
		connectAWS();
	}
	else
	{
		if (publishReading(r))
		{
			Serial.print("Published reading for "); Serial.println(r.time);
		}
	}
	delay(100);
}

void NTPConnect(void)
{
	Serial.print("Setting time using SNTP ");
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
}

void connect_wifi()
{
	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

	Serial.println("Connecting to Wi-Fi: " + String(WIFI_SSID));

	while (WiFi.status() != WL_CONNECTED)
	{
		delay(500);
		Serial.println("trying wifi...");
	}
}

void connectAWS()
{

	if (WiFi.status() != WL_CONNECTED)
		connect_wifi();

	Serial.println("Connecting to AWS IOT");
	if (client.connected())
	{
		Serial.println("AWS IoT Connected!");
		return;
	}
	else
	{
		NTPConnect();

		net.setTrustAnchors(&cert);
		net.setClientRSACert(&client_cert, &key);

		// Connect to the MQTT broker on the AWS endpoint we defined earlier
		client.setServer(AWS_IOT_ENDPOINT, 8883);

		while (!client.connect(THINGNAME))
		{
			Serial.println("trying aws IoT...");
			Serial.print(client.state());
			delay(500);
		}
		Serial.println("AWS IoT Connected!");
	}
	if (!client.connected())
	{
		Serial.println("AWS IoT Timeout!");
		return;
	}	
}

boolean publishReading(reading r)
{
	StaticJsonDocument<200> doc;
	doc["time"] = r.time;
	doc["rms_current"] = r.Irms;
	doc["power"] = r.watts;
	doc["watt_hours"] = r.watt_hours;
	char jsonBuffer[512];
	serializeJson(doc, jsonBuffer);
	// print to client
	return client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
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
		readValue = analogRead(sensorIn) - zero_ADC_Value;
		
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
	float energy = 0;
	float c_wh = 0.0;

	Voltage = getVPP();
	VRMS = (Voltage / 2.0) * 0.707;
	AmpsRMS = ((VRMS * 1000) / mVperAmp) - error;
	AmpsRMS = (AmpsRMS < 0.035) ? 0.0 : AmpsRMS;
	Watt = (AmpsRMS * 240);
	
	if (lastMillis != 0)
	{
		energy = Watt * (millis() - lastMillis);
		//weird data type thing here
		c_wh = energy / 3600000.0;		
		watt_hours += c_wh;
	}
	lastMillis = millis();
	time_t epochTime = timeClient.getEpochTime();

	read.time = epochTime;
	read.Irms = AmpsRMS;
	read.watts = Watt;
	read.watt_hours = watt_hours;

	return read;
}
