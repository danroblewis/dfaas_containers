import os

class D:
    def __init__(self):
        self.fn = None
    
    def set_fn(self, fn):
        self.fn = fn

    def run(self):
        pass
        # iterate in the way this is meant to iterate
        # 

d = D()

def dfaas(fn):
    global d
    d.set_fn(fn)
    return fn


@dfaas
def copy_rec(rec):
    return rec


def run():
    # get function_applications
    # make consumer for all joined input 
    # iterate over read messages
    # process with the @dfaas'd function
    # emit responses to the topics for this input topic
    # keep track of the most-recent input/output pair for a FunctionApplication
    # if the difference between the previous input/output pair and this input/output pair is greater than 10s
    #     emit it to a topic for the editor to consume
    #     maybe update an in-memory key-value database instead
    # increment time-series database for metrics

"""


cron->scrape_wunderground->alert_sfc_weather_temperature

cron {
    scrape_wonderground {
        out:wunderground_readings {
            topic = "weather_station_readings"

            alert_sfc_weather_temperature
            notify_discord
        }
        out:function_executions {
            log_function_executions
        }
    }
}


cron(spec="*/10 * * * * ") {
    scrape_wonderground(station_name="WX476JHH") {
        out:wunderground_readings => topic:weather_station_readings
        out:function_executions {
            log_function_executions(table_name="scrape_wunderground_log")
        }
    }
}
topic:weather_station_readings {
    alert_sfc_weather_temperature()
    notify_discord()
}



cron(spec="*/10 * * * *") {
    scrape_wonderground() {
        wunderground_readings = weather_station_readings
        function_executions = {
            log_function_executions(table_name="scrape_wunderground_log")
        }
    }
}
topic:weather_station_readings { alert_sfc_weather_temperature }
topic:weather_station_readings { notify_discord }


# if a function has only 1 parameter, you dont have to use a name
# parameters should be ordered

cron("*/10 * * * *") {
    scrape_wonderground() {
        out:wunderground_readings => topic:weather_station_readings
        out:function_executions {
            log_function_executions("scrape_wunderground_log")
        }
    }
}
topic:weather_station_readings() {
    alert_sfc_weather_temperature()
}
topic:weather_station_readings() {
    notify_discord()
}




"""

run()

