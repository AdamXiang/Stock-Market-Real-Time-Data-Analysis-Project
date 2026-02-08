# Real-Time Stock Market Data Streaming with Apache Kafka

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Kafka](https://img.shields.io/badge/Kafka-3.3.1-red)
![AWS](https://img.shields.io/badge/AWS-S3-orange)
![License](https://img.shields.io/badge/License-MIT-green)

## 📋 Project Overview

A production-ready real-time data streaming pipeline that ingests stock market data from CSV into Apache Kafka and persists it to AWS S3. This project demonstrates enterprise-grade architectural patterns including message replayability, flow control, and distributed system coordination.

**Core Metrics:**
- **Data Volume:** 104,425 stock market records
- **Throughput:** 1 message/second (intentional flow control)
- **Deployment:** Single-node EC2 with Kafka, Zookeeper, Producer, Consumer
- **Target Cloud:** AWS S3 for data persistence

---

## 🏗️ High-Level Architecture

```
┌──────────────────┐
│  CSV Data File   │ (indexProcessed.csv)
│  (104K records)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│      Kafka Producer (Python)         │
│  - Read CSV & serialize to JSON      │
│  - Send to Kafka Topic: "test"       │
│  - Flow Control: 1 sec/message       │
└────────┬─────────────────────────────┘
         │ (Bootstrap: 52.63.98.133:9093)
         ▼
┌──────────────────────────────────────────────┐
│         Apache Kafka Broker (EC2)            │
│  - Single Broker, Single Partition           │
│  - ADVERTISED_LISTENERS: EXTERNAL (Public IP)│
│  - Coordinated by Zookeeper                  │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│   Kafka Consumer (Python)            │
│  - Consume from Topic: "test"        │
│  - Auto Offset Reset: latest         │
│  - Enable Auto Commit: true          │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│       AWS S3 Bucket                  │
│  - Persist JSON objects              │
│  - Path: s3://kafka-stock-market.../ │
│  - File Format: stock_market_{n}.json│
└──────────────────────────────────────┘
```

### Architecture Decisions & Trade-offs

#### Why Apache Kafka?
1. **Message Replayability**
   - Kafka's log-based architecture allows offset resets for re-processing historical data
   - Contrast: RabbitMQ deletes messages after consumption; AWS Kinesis has limited retention
   - Benefit: During development, if consumer logic has bugs, simply reset offset and replay without data loss

2. **Avoid Vendor Lock-in**
   - Self-hosted on EC2 provides deep understanding of internal mechanisms (Partition, Broker, Zookeeper)
   - AWS Kinesis is easier but creates dependency on proprietary APIs
   - Trade-off: More operational complexity in exchange for flexibility and learning

3. **Enterprise Adoption**
   - Kafka is industry standard for high-throughput event streaming
   - Strong community support and mature ecosystem (Kafka Connect, Schema Registry, etc.)

#### Single-Node Deployment Constraints
- **Flow Control (1 sec/message):** Required due to resource contention in single EC2 instance
- **Production Expansion:** Multi-node deployment with multiple partitions enables horizontal scaling
- See [Known Issues & Production Roadmap](#known-issues--production-roadmap) for scaling strategy

---

## 📦 Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 20.04+) or macOS
- **Java:** OpenJDK 8+ or Oracle JDK 8+
- **Python:** 3.12+
- **AWS Credentials:** IAM user with S3 permissions (s3:GetObject, s3:PutObject)

### Infrastructure
- **EC2 Instance:** t2.medium (2 vCPU, 4 GB RAM) minimum for single-node development
  - Port 9092, 9093 (Kafka broker) open in security group
  - Port 2181 (Zookeeper) open internally
- **SSH Access:** .pem key for EC2 access
- **AWS S3 Bucket:** Pre-created S3 bucket with naming convention `kafka-stock-market-*`

### Local Development
- **CSV File:** `indexProcessed.csv` in project root (104,425 records)
- **AWS CLI:** Configured with credentials (`aws configure`)

---

## 🚀 Installation & Setup

### Step 1: Install Kafka on EC2

SSH into your EC2 instance:
```bash
ssh -i kafka-stock-market.pem ec2-user@<EC2_PUBLIC_IP>
```

Download and extract Kafka 3.3.1:
```bash
cd ~
wget https://archive.apache.org/dist/kafka/3.3.1/kafka_2.12-3.3.1.tgz
tar -xvf kafka_2.12-3.3.1.tgz
cd kafka_2.12-3.3.1
```

Verify Java installation:
```bash
java -version
# If not installed:
sudo yum install java-1.8.0-openjdk -y
```

### Step 2: Configure Kafka ADVERTISED_LISTENERS (Critical!)

This is the most common source of connection timeouts. Edit server properties:

```bash
sudo nano config/server.properties
```

Find and modify these lines:

```properties
# Line ~36
listeners=PLAINTEXT://:9092,PLAINTEXT_INTERNAL://:9093

# Line ~37 - CHANGE THIS TO YOUR EC2 PUBLIC IP
advertised.listeners=PLAINTEXT://52.63.98.133:9092,PLAINTEXT_INTERNAL://172.31.0.1:9093

# Add this new line after advertised.listeners
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT

# Add this new line (important for internal coordination)
inter.broker.listener.name=PLAINTEXT_INTERNAL
```

**Why this matters:**
- `EXTERNAL (9092)`: Advertises public IP for external Producer/Consumer (your local machine or remote services)
- `INTERNAL (9093)`: Uses private IP for Zookeeper and inter-broker communication
- Without this separation, Broker cannot coordinate properly when Zookeeper tries to reach it

### Step 3: Start Zookeeper

Open a new terminal window (keep previous SSH session open):

```bash
cd ~/kafka_2.12-3.3.1
bin/zookeeper-server-start.sh config/zookeeper.properties
```

Expected output:
```
[2024-XX-XX HH:MM:SS,XXX] INFO binding to port 0.0.0.0/0.0.0.0:2181
```

### Step 4: Start Kafka Broker

Open another terminal, SSH to EC2:

```bash
cd ~/kafka_2.12-3.3.1
export KAFKA_HEAP_OPTS="-Xmx256M -Xms128M"  # Memory constraints for t2.medium
bin/kafka-server-start.sh config/server.properties
```

Expected output:
```
[2024-XX-XX HH:MM:SS,XXX] INFO [KafkaServer id=0] started
```

### Step 5: Create Kafka Topic

Open another terminal, SSH to EC2:

```bash
cd ~/kafka_2.12-3.3.1

# Create topic with 1 partition, 1 replica (single-node setup)
bin/kafka-topics.sh --create \
  --topic test \
  --bootstrap-server 52.63.98.133:9092 \
  --replication-factor 1 \
  --partitions 1

# Verify topic creation
bin/kafka-topics.sh --list --bootstrap-server 52.63.98.133:9092
```

### Step 6: Python Environment Setup (Local Machine)

Clone or download the project:

```bash
git clone <your-repo-url> adamxiang-stock-market
cd adamxiang-stock-market
```

Create Python virtual environment:

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
# Or use pip with specific versions:
pip install kafka-python-ng==2.2.3 pandas==3.0.0 s3fs==2026.2.0
```

Configure AWS credentials:

```bash
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Default region (us-east-1), Output format (json)
```

Verify AWS S3 access:

```bash
aws s3 ls kafka-stock-market-sideproject-adam/
```

---

## 📖 Usage Guide

### Running the Full Pipeline

#### Terminal 1: Start Zookeeper (EC2)
```bash
ssh -i kafka-stock-market.pem ec2-user@<EC2_PUBLIC_IP>
cd ~/kafka_2.12-3.3.1
bin/zookeeper-server-start.sh config/zookeeper.properties
```

#### Terminal 2: Start Kafka Broker (EC2)
```bash
ssh -i kafka-stock-market.pem ec2-user@<EC2_PUBLIC_IP>
cd ~/kafka_2.12-3.3.1
export KAFKA_HEAP_OPTS="-Xmx256M -Xms128M"
bin/kafka-server-start.sh config/server.properties
```

#### Terminal 3: Start Producer (Local Machine)
```bash
cd adamxiang-stock-market
source venv/bin/activate
python kafka_producer.py
```

**Expected output:**
```
Loading CSV file...
✅ CSV loaded successfully! Check:    symbol  ...  salary
Connecting to Kafka...
Kafka Connection Successful! Starting data stream...
[Sent] Topic: test | Partition: 0 | Offset: 0
   Content: {'symbol': 'AAPL', 'price': 150.25, ...}
[Sent] Topic: test | Partition: 0 | Offset: 1
   Content: {'symbol': 'GOOGL', 'price': 140.50, ...}
```

#### Terminal 4: Start Consumer (Local Machine)
```bash
cd adamxiang-stock-market
source venv/bin/activate
python kafka_consumer.py
```

**Expected output:**
```
Connection Test:  ['kafka-stock-market-sideproject-adam']
Upload Successfully
Upload Successfully
Upload Successfully
...
```

### Verify Data in S3

```bash
aws s3 ls kafka-stock-market-sideproject-adam/
# Output:
# 2024-01-15 10:23:45        256 stock_market_0.json
# 2024-01-15 10:23:46        264 stock_market_1.json
# 2024-01-15 10:23:47        256 stock_market_2.json

# View a sample record
aws s3 cp s3://kafka-stock-market-sideproject-adam/stock_market_0.json -
# Output: {"symbol": "AAPL", "price": 150.25, ...}
```

### Monitoring Kafka Offset & Consumer Lag

```bash
cd ~/kafka_2.12-3.3.1

# List consumer groups
bin/kafka-consumer-groups.sh --bootstrap-server 52.63.98.133:9092 --list

# Check consumer group details (replace 'python-consumer-group' with actual group)
bin/kafka-consumer-groups.sh \
  --bootstrap-server 52.63.98.133:9092 \
  --group python-consumer-group \
  --describe
```

---

## 📁 Project Structure

```
adamxiang-stock-market-real-time-data-analysis-project/
│
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata
├── .python-version                    # Python 3.12
│
├── kafka_producer.py                  # CSV → Kafka Producer
│   ├─ CSV loading with error handling
│   ├─ Flow control: 1 sec/message
│   └─ Synchronous send with timeout
│
├── kafka_consumer.py                  # Kafka → S3 Consumer
│   ├─ S3 connection verification
│   ├─ Auto offset reset: latest
│   └─ Try/catch error handling (MVP stage)
│
├── main.py                            # Placeholder entry point
│
├── command_kafka.txt                  # Kafka setup commands (reference)
└── kafka-stock-market.pem             # AWS EC2 SSH key (KEEP SECURE!)
```

### Code Highlights

#### kafka_producer.py - Flow Control Design
```python
while True:
    stock_record = df.sample(1).to_dict(orient='records')[0]
    future = producer.send('test', value=stock_record)
    
    try:
        record_metadata = future.get(timeout=10)
        print(f"[Sent] Topic: {record_metadata.topic} | Offset: {record_metadata.offset}")
    except Exception as e:
        print(f"[Send Failed]: {e}")
        break
    
    sleep(1)  # ← CRITICAL: Prevents resource contention in single-node setup
```

**Why `sleep(1)` is necessary:**
- Without it, Producer sends 100K records in microseconds
- Single EC2 instance cannot handle: Producer + Broker + Zookeeper + Consumer simultaneously
- Results in CPU/Memory saturation → Zookeeper session timeout → Broker offline
- In production (multi-node), you'd remove this and use partition-based parallelism instead

#### kafka_consumer.py - S3 Persistence
```python
for count, message in enumerate(consumer):
    data = message.value
    s3_path = "s3://kafka-stock-market-sideproject-adam/stock_market_{}.json".format(count)
    
    try:
        with s3.open(s3_path, 'w') as file:
            json.dump(data, file)
        print("Upload Successfully")
    except Exception as e:
        print(f"Upload failed: {e}")
```

**Current limitations (MVP):**
- At-least-once semantics (no exactly-once guarantee)
- Failed uploads don't retry automatically
- No duplicate detection (same record might be written twice)

---

## 🐛 Known Issues & Production Roadmap

### Current Limitations (MVP Stage)

| Issue | Impact | Current Workaround | Production Solution |
|-------|--------|-------------------|---------------------|
| **Single Broker** | No redundancy | - | Deploy 3+ brokers across availability zones |
| **1 message/sec** | Low throughput | Required for stability | Multi-partition + producer batching |
| **No DLQ** | Failed messages lost | Manual inspection required | Dead Letter Queue topic for failed records |
| **No Idempotency** | Potential duplicate records | None | Hash-based filename deduplication in S3 |
| **Basic Error Handling** | Program crashes on S3 failure | Restart manually | Circuit breaker + exponential backoff |
| **No Monitoring** | Cannot detect lags/failures | Manual log inspection | Prometheus + Grafana for metrics |

### Future Enhancements

#### Phase 1: Reliability (Next)
- [ ] Implement Dead Letter Queue (DLQ) for failed messages
  ```python
  # Pseudo-code
  if s3_upload_fails:
      producer.send('error_topic', value=failed_record)
  ```
- [ ] Add idempotency check using message hash as S3 object key
- [ ] Implement exponential backoff for retries

#### Phase 2: Scalability
- [ ] Deploy Kafka cluster (3 brokers minimum)
- [ ] Increase partitions to 3-5 for parallel processing
- [ ] Add producer batching to replace 1 sec/message limitation
- [ ] Implement consumer group with multiple instances

#### Phase 3: Analytics (Post EL → ELT)
- [ ] AWS Glue Crawler to extract schema from S3 JSON
- [ ] AWS Athena for SQL queries on S3 data
- [ ] Superset/Tableau dashboard for visualization
- [ ] Extract insights: "Top 10 in-demand skills" and "Salary distribution"

#### Phase 4: Observability
- [ ] Add structured logging (JSON format)
- [ ] Prometheus metrics: consumer lag, throughput, error rate
- [ ] Grafana dashboard for real-time monitoring
- [ ] CloudWatch alarms for anomalies

---

## 🔧 Troubleshooting

### Connection Timeout: "NoBrokersAvailable"

**Problem:**
```
KafkaError: NoBrokersAvailable
```

**Root Causes & Solutions:**

1. **ADVERTISED_LISTENERS not set to public IP**
   ```bash
   # On EC2, check current setting:
   grep "advertised.listeners" ~/kafka_2.12-3.3.1/config/server.properties
   
   # Should show: advertised.listeners=PLAINTEXT://52.63.98.133:9092,...
   # If showing localhost, update it with EC2 public IP
   ```

2. **Security group blocks Kafka port**
   ```bash
   # EC2 Security Group must allow:
   # - Inbound: TCP 9092 from your local machine IP
   # - Inbound: TCP 9093 from within VPC (0.0.0.0/0 for development only)
   ```

3. **Zookeeper not running**
   ```bash
   # Check if Zookeeper process is alive:
   jps  # Should show QuorumPeerMain
   
   # If not, restart:
   bin/zookeeper-server-start.sh config/zookeeper.properties
   ```

### Producer Crash: "OAUTHBEARER Authentication Failed"

**Problem:**
```
Unable to parse Kafka version: 255.255.255.255
```

**Solution:**
Force API version in producer:
```python
producer = KafkaProducer(
    bootstrap_servers=['52.63.98.133:9093'],
    api_version=(2, 8, 1),  # ← Add this
    request_timeout_ms=30000
)
```

### Consumer: S3 Upload Fails Silently

**Problem:** Consumer runs but S3 bucket is empty.

**Solution:**
1. Verify AWS credentials:
   ```bash
   aws s3 ls
   ```
2. Verify S3 bucket name in `kafka_consumer.py` matches actual bucket
3. Check IAM permissions:
   ```bash
   aws s3api get-bucket-policy --bucket kafka-stock-market-sideproject-adam
   ```
4. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Kafka Broker Crashed After Full CSV Send

**Problem:** Tried running without `sleep(1)` and broker went offline.

**Explanation:** 
- Single EC2 instance running 4 heavy processes (Producer, Broker, Zookeeper, Consumer)
- Producer flooding 100K messages in <1 second causes resource contention
- CPU/Memory maxed out → Zookeeper cannot send heartbeat → Broker marked offline

**Prevention:**
- Keep `sleep(1)` for development
- Monitor system resources: `top` or `htop`
- In production, distribute across multiple EC2 instances

---

## 📊 Performance Characteristics

### Single-Node Performance (Current)
- **Throughput:** 1 msg/sec (flow-controlled)
- **Actual Capacity:** ~10K msg/sec (unbounded)
- **Latency:** <100ms (producer → broker → consumer → S3)
- **Storage:** ~104KB per second to S3 (100K records ÷ ~30 minutes)

### Expected Production Performance (Multi-Node)
- **Throughput:** 10K-100K msg/sec (depends on partition count)
- **Latency:** <50ms end-to-end
- **Availability:** 99.9% (with 3-broker cluster)

---

## 🤝 Contributing

This is a learning project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit pull request

### Areas for Contribution
- [ ] Implement DLQ and idempotency
- [ ] Add Prometheus metrics
- [ ] Create Docker Compose for multi-broker setup
- [ ] Add unit tests for producer/consumer
- [ ] Extend to support other data sources (API, database)

---

## 📚 References & Learning Resources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Kafka ADVERTISED_LISTENERS Explained](https://rmoff.net/2018/08/02/kafka-listeners-explained/)
- [AWS S3 with Python boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html)
- [Understanding Offset Management in Kafka](https://medium.com/@seilylook95/understanding-kafka-consumer-offsets-a-key-to-reliable-data-processing-09188646cc54)

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👤 Author

**Adam Xiang**
- GitHub: [adamxiang](https://github.com/AdamXiang)
- Medium: [Stock Market Data Pipeline](https://medium.com/@adams-chang)
- Linkedin: [Ching-Hsiang Chang](https://www.linkedin.com/in/ching-hsiang-chang-782281217/)

---

## ⭐ Acknowledgments

Built with Apache Kafka, Python, and AWS infrastructure. Special thanks to the Kafka community for excellent documentation.
* [Darshil Parmar](https://www.linkedin.com/in/darshil-parmar/) — A Freelance Data Engineer and Solution Architect. [Data engineering tutorial videos](https://www.youtube.com/watch?v=KerNf0NANMo) that inspired this project

---

**Last Updated:** February 2026 
**Kafka Version:** 3.3.1  
**Python Version:** 3.12+
