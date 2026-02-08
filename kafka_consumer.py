import pandas as pd
from kafka import KafkaConsumer
from time import sleep
from json import loads
import json
from s3fs import S3FileSystem


# Create the kafka producer
consumer = KafkaConsumer(
                         'test',
                         bootstrap_servers=['52.63.98.133:9093'],
                         value_deserializer=lambda x: loads(x.decode('utf-8')),
                         # [Key 2] Offset Configuration (Auto Offset Reset)
                         # 'earliest': Reads from the beginning of the topic history (Ideal for testing to verify past data)
                         # 'latest': (Default) Reads only new messages sent after connection (Ideal for real-time monitoring)
                         auto_offset_reset='latest',
                         # automatically submit Offset 
                         enable_auto_commit=True)


# for message in consumer:
#   data = message.value
#   print(f"Receiving message:")
#   print(f"   Content (Value): {data}")
#   print(f"   Data type: {type(data)}") 

try:
  s3 = S3FileSystem()
  print(f"Connection Test: ", s3.ls('kafka-stock-market-sideproject-adam'))

except:
  print("Connection failed: please check AWS Configure or IAM Role: {e}")
  exit()

for count, message in enumerate(consumer):
  data = message.value

  s3_path = "s3://kafka-stock-market-sideproject-adam/stock_market_{}.json".format(count)

  try:
    with s3.open(s3_path, 'w') as file:
      json.dump(data, file)
    print("Upload Successfully")
  except Exception as e:
    print(f"Upload failed: {e}") 






