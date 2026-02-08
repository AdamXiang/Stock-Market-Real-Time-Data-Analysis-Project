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
                         # 【關鍵 2】Read offset (Auto Offset Reset)
                         # 'earliest': 當你是新的消費者，從「最舊」的訊息開始讀 (適合測試，確保能讀到剛才發送的)
                         # 'latest': (預設值) 只讀「啟動之後」才送進來的新訊息 (適合即時監控)
                         auto_offset_reset='latest',
                         # automatically submit Offset 
                         enable_auto_commit=True)


# for message in consumer:
#   data = message.value
#   print(f"Receiving message:")
#   print(f"   Content (Value): {data}")
#   print(f"   Data type: {type(data)}")  # 驗證它真的是 dict

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






