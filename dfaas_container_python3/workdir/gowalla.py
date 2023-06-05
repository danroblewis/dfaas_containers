#!/usr/bin/python3

import pymongo
import os
conn = pymongo.MongoClient(os.environ['MONGODB_HOST'], int(os.environ['MONGODB_PORT']), username=os.environ['MONGODB_USER'], password=os.environ['MONGODB_PASSWORD'])
coll = conn.test.dfaas_functions

fn_rec = conn.test.dfaas_functions.find_one({ 'name': os.environ['FUNCTION_NAME'] })
fn_code = fn_rec['code']
exec(fn_code)

