import json
import kafka
import os
import sys

consumer = kafka.KafkaConsumer(sys.argv[1], bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
while True:
    print(next(consumer))
