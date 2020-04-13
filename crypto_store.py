import binance_data
from influxdb import InfluxDBClient
from multiprocessing import Process
import sys
import time

# Default HOST and PORT for the local instance of InfluxDB
HOST = 'localhost'
PORT = 8086

# Name of the databse where the values needs to be stored
DATABASE = "crypto_ticker"

# Various measurements to be used for storing various ticker data
MEASUREMENT_1M = 'CRYPTO_1M'
MEASUREMENT_5M = 'CRYPTO_5M'
MEASUREMENT_15M = 'CRYPTO_15M'
MEASUREMENT_30M = 'CRYPTO_30M'
MEASUREMENT_1H = 'CRYPTO_1H'

# Time precision of the Binance server is in miliseconds
PRECISION = 'ms'





def database_setup():

  # Initialise the InfluxDB client
  client = InfluxDBClient(HOST, PORT)

  # Create the required database, if the databse is already present
  # this would just return without any exception
  client.create_database(DATABASE)
  client.switch_database(DATABASE)
  return client



def convert_to_json_schema(measurement, OHLC_data):
  """
  To convert obtained data into the required format for the database insertion
  Args:
    measurement: <str> choose from available measurements
    OHLC_data: <dict> data returned by the binance_data.retrieve_OHLC

  Returns:
    <list> json_body conforming to the schema required by InfluxDB
  """
  json_body = []

  for market in OHLC_data:
    json_body.append(
        _format(measurement, market, OHLC_data[market])
    )
  return json_body



def record_update(client):
  """
  A full pipeline from fetch (from Binance) to insert (InfluxDB)
  """
  print('start')
  OHLC_data, errors = binance_data.retrieve_OHLC(binance_data.MARKETS)
  # print(OHLC_data)
  json_body = convert_to_json_schema(MEASUREMENT_1M, OHLC_data)
  # print(json_body)
  client.write_points(json_body,time_precision=PRECISION)
  print('stop')



def run_data_collection(client):
  """
  Now the primary functionality if to retrieve market data from binance
  every 1 minute (1m Ticker). To accomplish that 'record_update' need to
  be scheduled to run every one second. time.sleep() is a blocking call,
  therefore using the multiprocessing module to add parallism to the module
  The main functionality - spawn a new 'record_update' process every 1 minute
  Args:
    client: database client which need to be used to store the collected data

  Returns:
    <None>
  """

  process_list = []

  try:
    while True:
      # Initialize a process
      p = Process(target=record_update, args=(client,))
      # Start the process to run independently of main
      p.start()
      # TODO: Define a function which can act as a garbage collector, which can periodicly
      # check for not active processes and free the resources
      process_list.append(p)
      time.sleep(60)
  except KeyboardInterrupt:
    # Kill all the processes which are alive
    for i in process_list:
      # If the process is still running, kill the process - SIGKILL
      if i.is_alive():
        i.kill()
      time.sleep(0.1)
      # Free all the resources associated with the process
      i.close()



def _format(measurement, market, OHLC):
  """
  To format the data according to the json schema
  Args:
    market: <str>
    OHLC: <dict> data corresponding to the 'market'

  Returns:
    <dict> element of the body of the schema
  """

  json_elem = {
    "measurement": measurement,
    "tags":{
      "Market": market
    },
    "time": OHLC['open_time'],
    "fields":{
      "Open":OHLC['open'],
      "Close":OHLC['close'],
      "High":OHLC['high'],
      "Low":OHLC['low'],
      "Volume":OHLC['volume']
    }

  }

  return json_elem





if __name__=='__main__':

  # Populate the list of markets listed on Binance
  binance_data.update_market_list()

  # Setup the database for storing market data
  client = database_setup()

  if len(sys.argv) == 2:
    if sys.argv[1] == 'run':
      run_data_collection(client)
    else:
      print("Enter valid argument")
      exit(1)
  



