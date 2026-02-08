import pandas as pd
from kafka import KafkaProducer
from time import sleep
from json import dumps
import json


# 1. Load CSV data
print("Loading CSV file...")
try:
  df = pd.read_csv(f"indexProcessed.csv")
  print(f"✅ CSV loaded successfully! Check: {df.head()}")
except FileNotFoundError:
  print("❌ Error: 'indexProcessed.csv' not found. Please check the file path.")
  exit()

# 2. Initialize Kafka Producer
print("Connecting to Kafka...")
producer = KafkaProducer(
   bootstrap_servers=['52.63.98.133:9093'],
   value_serializer=lambda x: dumps(x).encode('utf-8'),
   # Force API version to bypass version negotiation errors (solves NoBrokersAvailable)
    api_version=(2, 8, 1), 
    request_timeout_ms=30000)


print("Kafka Connection Successful! Starting data stream...")


while True:
  # Sample one raw from df and convert it into dict
  stock_record = df.sample(1).to_dict(orient='records')[0]

  # Send the message and put into buffer
  future = producer.send('test', value=stock_record)

  # [Optional] Wait for result (Synchronous Blocking)
  # This makes the process slower but ensures data is definitely received by the server.
  # Comment out this try/except block for maximum performance (Fire-and-forget).
  try:
      record_metadata = future.get(timeout=10)
      print(f"[Sent] Topic: {record_metadata.topic} | Partition: {record_metadata.partition} | Offset: {record_metadata.offset}")
      print(f"   Content: {stock_record}")
  except Exception as e:
      print(f"[Send Failed]: {e}")
      break # Exit loop if connection is lost

  # Simulate real-time delay (1 second per message)
  sleep(1)
