import kafka
import os
import time
import sys

producer = kafka.KafkaProducer(bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
while True:
    r = producer.send(sys.argv[1], b'{"value": "qwer"}')
    print(r)
    time.sleep(0.5)
