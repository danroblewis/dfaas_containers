#!/usr/bin/python3

import pymongo
import json
import kafka
import os
import sys
from datetime import datetime

print("\n"*10)
function = None
fname = os.environ['FUNCTION_NAME']

def dfaas(fn):
    global function, fname
    if os.environ['FUNCTION_NAME'] == fn.__name__:
        function = fn
        fname = fn.__name__
    return fn


class Record:
    def __init__(self, attributes):
        try:
            for name, value in attributes.items():
                self.__setattr__(name, value)
        except Exception as e:
            print(e)


conn = pymongo.MongoClient(os.environ['MONGODB_HOST'], int(os.environ['MONGODB_PORT']), username=os.environ['MONGODB_USER'], password=os.environ['MONGODB_PASSWORD'])
functions = conn.test.dfaas_functions
function_applications = conn.test.dfaas_function_applications


def get_mappings(collection, fname):
    fn_app_lists = collection.find({ "function_name": fname })

    maps = {} # input topic -> map of (fn_topic_name -> real_topic)

    for fn_app in fn_app_lists:
        inp = fn_app['input_topic']

        if inp not in maps:
            maps[inp] = []

        maps[inp].append(fn_app['output_topics'])
        print(json.dumps(maps, indent=4))

    return maps


def setup_consumer(consumer, fname, mappings):
    print('doing setup_consumer')
    input_topic_names = list(mappings.keys())
    if consumer:
        consumer.close()
    consumer = kafka.KafkaConsumer(*input_topic_names, bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
    consumer.subscribe(input_topic_names)
    return consumer


mappings = {}
consumer = None

producer = kafka.KafkaProducer(bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])

refresh_interval = 10
last_refresh = datetime(1970,1,1)
code = None

while True:
    now = datetime.now()
    tdiff = now-last_refresh
    if tdiff.total_seconds() >= refresh_interval:
        last_refresh = now

        fn = functions.find_one({ "name": fname })
        print(fname, fn)
        if code != fn['code']:
            print(now, "refreshing function", fname)
            code = fn['code']
            exec(code)

        new_mappings = get_mappings(function_applications, fname)
        if json.dumps(mappings) != json.dumps(new_mappings):
            print('fixing consumer')
            mappings = new_mappings
            consumer = setup_consumer(consumer, fname, mappings)


    r = consumer.poll(timeout_ms=100, max_records=200)
    for rr in sum(r.values(), []):
        t = rr.value.decode('utf-8')
        if '{' not in t: continue
        try:
            rec = json.loads(t)
        except:
            print('failed to parse', t)
        rec = Record(rec)
        ret = function(rec)
        print('retval:', ret)

        topics = mappings[rr.topic]
        for topic in topics:
            if 'default' in topic:
                s = producer.send(topic['default'], json.dumps(ret).encode())


