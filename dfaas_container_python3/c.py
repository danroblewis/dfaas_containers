import yaml

a="""
functions:
- function_name: cron
  parameters:
  - "*/10 * * * *"
  outputs:
  - name: cron_initiator
    topic: cron_12345_scrape_wunderground

- function_name: scrape_wunderground
  input: cron_12345_scrape_wunderground
  outputs:
  - name: weather_station_readings
    topic: wunderground_readings
  - name: function_executions
    topic: scrape_wunderground_12345_function_executions

- function_name: log_function_executions
  parameters:
  - "scrape_wunderground_log"
  input: scrape_wunderground_12345_function_executions

- function_name: alert_sfc_weather_temperature
  input: wunderground_readings

- function_name: notify_discord
  input: wunderground_readings
"""

print('digraph a {')

y = yaml.safe_load(a)
for fn in y['functions']:
    n = fn['function_name']
    print('"' + fn['function_name'] + '" [style=filled color=lightpink]')
    if 'input' in fn:
        print(f"\"{fn['input']}\"->\"{n}\" [style=filled color=lightblue]")
    if 'outputs' in fn:
        for output in fn['outputs']:
            print(f"\"{n}\"->\"{output['topic']}\" [label=\"{output['name']}\"]")
            print(f"\"{output['topic']}\" [style=filled color=darkseagreen1]")

print("}")
