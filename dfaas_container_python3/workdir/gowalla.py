#!/usr/bin/python3

import pymongo
import json
import kafka
import os
import sys
import datetime
import inspect
import time
import traceback
from contextlib import redirect_stdout
import io
import base64

print("\n"*10)
function = None
fname = os.environ['FUNCTION_NAME']

def dfaas(fn):
    global function, fname
    if os.environ['FUNCTION_NAME'] == fn.__name__:
        function = fn
        fname = fn.__name__
    return fn

def debug(*args, **kwargs):
  if os.environ.get('LOGLEVEL') == 'DEBUG':
    print('DEBUG', args, kwargs)

def info(*args, **kwargs):
  if os.environ.get('LOGLEVEL') in ['DEBUG', 'INFO']:
    print('INFO', args, kwargs)


conn = pymongo.MongoClient(os.environ['MONGODB_HOST'], int(os.environ['MONGODB_PORT']), username=os.environ['MONGODB_USER'], password=os.environ['MONGODB_PASSWORD'])
functions = conn.test.dfaas_functions
function_applications = conn.test.dfaas_function_applications

def convert_topic_names(topic_names):
    a = []
    for n in topic_names:
        if n.startswith('dyntopic_'):
            a.append(base64.b64decode(n.replace('dyntopic_','') + '==').decode())
        else:
            a.append(n)
    return a

def get_mappings(collection, fname):
    fn_app_lists = collection.find({ "fname": fname })
    maps = {} # input topic -> map of (fn_topic_name -> real_topic)
    for applist in fn_app_lists:
        for input_topic, apps in applist['applications'].items():
            if input_topic not in maps: maps[input_topic] = []

            maps[input_topic] += apps

    return maps


def setup_consumer(consumer, fname, mappings):
    input_topic_names = list(mappings.keys())
    if None in input_topic_names:
        input_topic_names.remove(None)
    if "null" in input_topic_names:
        input_topic_names.remove("null")
    if consumer:
        consumer.close()
    if len(input_topic_names) == 0:
        return None
    ablitterate = convert_topic_names(input_topic_names)
    print("reading from topics:", input_topic_names)
    consumer = kafka.KafkaConsumer(*input_topic_names, bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
    consumer.subscribe(input_topic_names)
    return consumer


mappings = {}
consumer = None

producer = None
while producer is None:
  try:
    producer = kafka.KafkaProducer(bootstrap_servers=[ os.environ['KAFKA_ADDRESS'] ])
  except kafka.errors.NoBrokersAvailable as e:
    print("failed to boot")
    print(traceback.format_exc())
    time.sleep(5)

refresh_interval = 10
last_refresh = datetime.datetime(1970,1,1)
code = None
log_stdout = False



while True:
    now = datetime.datetime.now()
    tdiff = now-last_refresh
    if tdiff.total_seconds() >= refresh_interval:
        last_refresh = now

        new_mappings = get_mappings(function_applications, fname)
        if json.dumps(mappings) != json.dumps(new_mappings):
            mappings = new_mappings
            consumer = setup_consumer(consumer, fname, mappings)

        fn = functions.find_one({ "name": fname })
        log_stdout = (now.timestamp() - fn['last_update']) < 10*60 # updated within 10 minutes
        if code != fn['code']:
            print(now, "refreshing function", fname)
            code = fn['code']
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    exec(code)
                except Exception as e:
                    print(traceback.format_exc())
                    s = f.getvalue()
                    if log_stdout and len(s) > 0:
                        producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
                    continue
            s = f.getvalue()
            if log_stdout and len(s) > 0:
                producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
            function = locals()[fname]

    # TODO: not sure how to make this support paramaters. i think the functions need to be called async.
    if "null" in mappings: # this is an output-only function
        debug('is output-only function')
        if inspect.isgeneratorfunction(function):
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    ret = next(function())
                except Exception as e:
                    print(traceback.format_exc())
            s = f.getvalue()
            if log_stdout and len(s) > 0:
                producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
        else:
            f = io.StringIO()
            debug('is one shot function')
            with redirect_stdout(f):
                try:
                    ret = function()
                except Exception as e:
                    print(traceback.format_exc())
            s = f.getvalue()
            if log_stdout and len(s) > 0:
                producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
        topics = mappings["null"]
        # do not propogate return values if the value is just None
        if ret is None:
            continue
        ret = json.dumps(ret).encode()
        for topic in topics:
            for out in topic['outputs']:
                if 'default' in out and out['default']:
                    producer.send(out['default'], ret)

    #elif :  # this is an input-only function

    else: # this is good old fashion input-to-output function
        debug('normal input-output function')
        if consumer is None:
            print("No topics found to read from. waiting.")
            time.sleep(20)
        else:
            r = consumer.poll(timeout_ms=100, max_records=201)
            for rr in sum(r.values(), []):
                info(rr.value)
                applications = mappings[rr.topic]
                for application in applications:
                    t = rr.value.decode('utf-8')
                    if '{' not in t: continue
                    try:
                        rec = json.loads(t)
                    except:
                        print('failed to parse incoming message', t)

                    if fname == 'print_rec':
                        debug('this is print_rec')
                        f = io.StringIO()
                        with redirect_stdout(f):
                            try:
                                ret = function(rec, **application['params'])
                            except Exception as e:
                                print(traceback.format_exc())
                        s = f.getvalue()
                        print(s)
                        if log_stdout and len(s) > 0:
                            producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
                    else:
                        if inspect.isgeneratorfunction(function):
                            debug('is generator')
                            gen = function(rec, **application['params'])
                            finished = False
                            while not finished:
                                f = io.StringIO()
                                with redirect_stdout(f):
                                    try:
                                        ret = next(gen)
                                        # do not propogate return values if the value is just None
                                        if ret is None:
                                            continue
                                        if not isinstance(ret, dict):
                                            ret = { "value": ret }
                    
                                        for out in application['outputs']:
                                            if 'default' in out and out['default']:
                                                 producer.send(out['default'], json.dumps(ret).encode())

                                    except StopIteration:
                                        finished = True
        
                                    except Exception as e:
                                        print(traceback.format_exc())
                                s = f.getvalue()
                                if log_stdout and len(s) > 0:
                                    producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())
                        else:
                            debug('is not generator')
                            f = io.StringIO()
                            with redirect_stdout(f):
                                try:
                                    ret = function(rec, **application['params'])
                                     # do not propogate return values if the value is just None
                                    if ret is None:
                                        continue
                                    if not isinstance(ret, dict):
                                        ret = { "value": ret }
                
                                    for out in application['outputs']:
                                        if 'default' in out and out['default']:
                                             producer.send(out['default'], json.dumps(ret).encode())
    
                                except Exception as e:
                                    print(traceback.format_exc())

                            s = f.getvalue()
                            if log_stdout and len(s) > 0:
                                producer.send(f"{fname}_stdout", json.dumps({ "stdout": s, "tstamp": datetime.datetime.now().timestamp() }).encode())


