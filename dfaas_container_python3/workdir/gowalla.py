#!/usr/bin/python3

import kafka
import pymongo
import os
import json
import time

conn = pymongo.MongoClient(os.environ['MONGODB_HOST'], int(os.environ['MONGODB_PORT']), username=os.environ['MONGODB_USER'], password=os.environ['MONGODB_PASSWORD'])
coll = conn.test.dfaas_functions
filter = { 'name': os.environ['FUNCTION_NAME'] }
fn_rec = conn.test.dfaas_functions.find_one(filter)
print('fn record', fn_rec)
fn_code = fn_rec['code']

consumer = None
emit = None
delay = None

# if this function has an INPUT_TOPIC defined, read and process via input topic
if 'INPUT_TOPIC' in os.environ:
    consumer = kafka.KafkaConsumer(os.environ['INPUT_TOPIC'], bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])

if 'OUTPUT_TOPIC' in os.environ:
    producer = kafka.KafkaProducer(bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
    def _emit(outrec):
        producer.send(os.environ['OUTPUT_TOPIC'], outrec)
    emit = _emit

elif 'TIMER' in os.environ:
    delay = int(os.environ['TIMER'])



if consumer:
    i = 0
    for rec in consumer:
        print("message: ", i)
        i += 1
        exec(fn_code)
elif delay:
    i = 0
    while True:
        print("message: ", i)
        i += 1
        exec(fn_code)
        time.sleep(delay)
else:
    print("dude wtf, there is literally nothing for me to do.")
    print("like, you didn't give me an INPUT_TOPIC, and you didn't give me a TIMER (which I woudl use for a sleep value")
    print("you gotta gie me something.")
    print("this is just fucking ridiculous.")


