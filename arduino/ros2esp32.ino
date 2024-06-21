#include <ros2arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// 와이파이 정보
const char* ssid = "cropeco";
const char* password = "asdfasdf";

// ROS2 설정
#define AGENT_IP "192.168.1.229"  // ROS2 에이전트의 IP 주소
#define AGENT_PORT 2018           // ROS2 에이전트의 포트 번호

// 수직 스테퍼 모터 핀 정의
const int vertDirPin = 18;
const int vertStepPin = 19;
const int vertEnablePin = 23;

// 수평 스테퍼 모터 핀 정의
const int horzDirPin = 25;
const int horzStepPin = 26;
const int horzEnablePin = 27;

// 스테퍼 모터 설정
const int stepsPerRevolution = 2000;
const int motorSpeed = 500;  // 스텝 간격 (마이크로초)

WiFiUDP udp;

void moveMotor(std_msgs::String* msg, void* arg) {
  (void)(arg);
  String direction = msg->data;

  if (direction == "up") {
    Serial.println("upupppp");
    // 위로 이동
    digitalWrite(vertDirPin, HIGH);
    digitalWrite(vertEnablePin, LOW);
    for (int i = 0; i < stepsPerRevolution; i++) {
      digitalWrite(vertStepPin, HIGH);
      delayMicroseconds(motorSpeed);
      digitalWrite(vertStepPin, LOW);
      delayMicroseconds(motorSpeed);
    }
    digitalWrite(vertEnablePin, HIGH);
  } else if (direction == "down") {
    // 아래로 이동
    digitalWrite(vertDirPin, LOW);
    digitalWrite(vertEnablePin, LOW);
    for (int i = 0; i < stepsPerRevolution; i++) {
      digitalWrite(vertStepPin, HIGH);
      delayMicroseconds(motorSpeed);
      digitalWrite(vertStepPin, LOW);
      delayMicroseconds(motorSpeed);
    }
    digitalWrite(vertEnablePin, HIGH);
  } else if (direction == "left") {
    // 왼쪽으로 이동
    digitalWrite(horzDirPin, LOW);
    digitalWrite(horzEnablePin, LOW);
    for (int i = 0; i < stepsPerRevolution; i++) {
      digitalWrite(horzStepPin, HIGH);
      delayMicroseconds(motorSpeed);
      digitalWrite(horzStepPin, LOW);
      delayMicroseconds(motorSpeed);
    }
    digitalWrite(horzEnablePin, HIGH);
  } else if (direction == "right") {
    // 오른쪽으로 이동
    digitalWrite(horzDirPin, HIGH);
    digitalWrite(horzEnablePin, LOW);
    for (int i = 0; i < stepsPerRevolution; i++) {
      digitalWrite(horzStepPin, HIGH);
      delayMicroseconds(motorSpeed);
      digitalWrite(horzStepPin, LOW);
      delayMicroseconds(motorSpeed);
    }
    digitalWrite(horzEnablePin, HIGH);
  }
}

class MotorSub : public ros2::Node {
public:
  MotorSub() : Node("ros2arduino_motor_node") {
    this->createSubscriber<std_msgs::String>("motor_direction", (ros2::CallbackFunc)moveMotor, nullptr);
  }
};

void setup() {
  // 시리얼 통신 시작
  Serial.begin(115200);

  // 핀 모드 설정
  pinMode(vertDirPin, OUTPUT);
  pinMode(vertStepPin, OUTPUT);
  pinMode(vertEnablePin, OUTPUT);
  pinMode(horzDirPin, OUTPUT);
  pinMode(horzStepPin, OUTPUT);
  pinMode(horzEnablePin, OUTPUT);

  // 모터 비활성화
  digitalWrite(vertEnablePin, HIGH);
  digitalWrite(horzEnablePin, HIGH);

  // 와이파이 연결
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // ROS2 초기화
  ros2::init(&udp, AGENT_IP, AGENT_PORT);
}

void loop() {
  static MotorSub MotorNode;
  ros2::spin(&MotorNode);
}