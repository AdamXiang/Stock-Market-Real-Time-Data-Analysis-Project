import pandas as pd
from kafka import KafkaProducer
from json import dumps
import json


# Create the kafka producer
producer = KafkaProducer(bootstrap_servers=['52.63.98.133:9093'],
                         value_serializer=lambda x: dumps(x).encode('utf-8'))


data =  {'hello': 'world'}

# Send the message and put into buffer
future = producer.send('test', value=data)

# Wait for the result
try:
    # get(timeout=10) forcely pause the program until kafka server returns "get it"
    record_metadata = future.get(timeout=10)
    print(f"Send Successful")
    print(f"   Topic: {record_metadata.topic}")
    print(f"   Partition: {record_metadata.partition}")
    print(f"   Offset: {record_metadata.offset}")
except Exception as e:
    print(f"Send failed: {e}")
