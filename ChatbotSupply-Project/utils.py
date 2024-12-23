from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
#from langchain.memory import ChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory


import pandas as pd
import numpy as np
import os
import json
import string
import mysql.connector
from statsmodels.tsa.arima.model import ARIMA
from datetime import timedelta

#initialize OPENAI API with Key
os.environ["OPENAI_API_KEY"] = 'Key Here'
client = ChatOpenAI(model = "gpt-3.5-turbo-0125", temperature=0)

call_signal = 0
history_prompt = []
#Load the model
#model = ARIMAResults.load("/static/model/arima_model.pkl")

# Function to connect to the database
def DB_Connection(host,user,password,database):
  db = mysql.connector.connect(
      host = host,
      user = user,
      password = password,
      database = database
  )
  return db

# Function to retrieve data from the database
def days_taken(distance):
  return (distance // 50)

# To predict arrival date
def forecast_arrival_dates(product_id):
  forecast_steps = 10
  db_connection = DB_Connection("127.0.0.1","root","smartagents_3","SupplyChainInventory")
  print("Database Connection Successful")


  query = '''Select * from transaction_Db
                where stockIn_stockOut = 0''' 

  

  df = pd.read_sql(query, con= db_connection)

  df["ShippingDate"] = pd.to_datetime(df["ShippingDate"])
  df["DaysTaken"] = df["Shipping_Miles"].apply(days_taken)

  """
    Predict arrival dates based on ARIMA model for a specific product.

    Parameters:
        df: DataFrame with historical data.
        product_id: Product ID to forecast for.
        forecast_steps: Number of days to forecast.
    """
    # Filter data for the specific product
  product_df = df[df['ProductID'] == product_id][['ShippingDate', 'DaysTaken']]
  product_df = product_df.rename(columns={'ShippingDate': 'ds', 'DaysTaken': 'cnt'}).sort_values(by='ds')

  if product_df.empty:
      print(f"No data available for product {product_id}.")
      return

  product_df.set_index('ds', inplace=True)

    # Run ARIMA model
  p, d, q = 2, 1, 1  # ARIMA parameters
  print(f"Running ARIMA for product {product_id}...")
  model = ARIMA(product_df['cnt'], order=(p, d, q))
  model_fit = model.fit()

    #model_fit.save("")
    # Forecast future Days Taken
  future_days_taken = model_fit.forecast(steps=forecast_steps)

    # Generate Future Shipping Dates
  last_date = product_df.index[-1]
  future_shipping_dates = [last_date + timedelta(days=i) for i in range(1, forecast_steps + 1)]

    # Predict Arrival Dates
  forecast_df = pd.DataFrame({
        'ProductID': product_id,
        'ShippingDate': future_shipping_dates,
        'ForecastDaysTaken': future_days_taken
    })

    # Calculate Arrival Dates (exclude time)
  forecast_df['ForecastArrivalDate'] = (
        forecast_df['ShippingDate'] + pd.to_timedelta(forecast_df['ForecastDaysTaken'], unit='D')
    ).dt.date


    # Display Results
  print("\nPredicted Arrival Dates for Product:", product_id)
  print(forecast_df)
  forecast_df["ForecastArrivalDate"] = forecast_df["ForecastArrivalDate"].apply(lambda x : str(x))
  result = forecast_df.tail(1).to_json()
  return result

# Function to insert information into database
def Insert_to_DB(ItemName, Quantity):
  db_connection = DB_Connection("127.0.0.1","root","smartagents_3","SupplyChainInventory")
  print("DB connection successful")

  DB_Cursor = db_connection.cursor()
  DB_Cursor.callproc('InsOrders', [ItemName,Quantity])

  db_connection.commit()

  print(DB_Cursor.rowcount, "records inserted")

  DB_Cursor.close()
  db_connection.close()
  return Quantity + "units of " + ItemName + "(s) has been ordered."

#   Function to retrieve data from the database
def Ret_Qty_from_DB(ItemName):
  db_connection = DB_Connection("127.0.0.1","root","smartagents_3","SupplyChainInventory")
  print("Database Connection Successful")
  DB_Cursor = db_connection.cursor()

  cmdstring = '''Select 
                sum(case when t.stockin_stockout = FALSE then t.quantitySold else 0 end) - 
                sum(case when t.stockin_stockout = TRUE then t.quantitySold else 0 end) as 'Quantity'
                from Products p left join Transaction_Db t
                on p.ProductID = t.ProductID
                where p.ProductName = %s or p.ProductID = %s'''
  val = (ItemName,ItemName,)

  DB_Cursor.execute(cmdstring,val)

  result = DB_Cursor.fetchone()
  #print(result)
  x=''

  for s in result:
    print(s)
    x=s
  return str(x)

# Funtion to output the availability of admission space based on age range
def send_email(eID: string):
  db_connection = DB_Connection("127.0.0.1","root","smartagents_3","SupplyChainInventory")
  print("Database Connection Successful")
  return "Email Successfully sent to " + eID + ". Thank you."
  
history = ChatMessageHistory()
history.add_ai_message('You are an intelligent Assistant')

# LangChain single column
def asksingle_langchain_ai_agent(system_prompt,user_prompt, model='gpt-3.5-turbo-0125',temp=0):

  temperature = temp

  function_descriptions = [
      {
          "name":"Insert_to_DB",
          "description":"Tell a user about the quantity of a product ordered and the arrival date. For instance 'Your order for 3 Fresh Tomatoes has been shipped and arrives on 5th January, 2025'",
          "parameters":{
              "type":"object",
              "properties":{
                  "Quantity":{
                    "type": "string",
                    "description":"The quantity of the Item / product shipped",
                  },
                  "ItemName":{
                    "type": "string",
                    "description":"The name of the Item / product shipped",
                    },
              },
              "required":["Quantity","ItemName"],
              "additionalProperties":False,
          },
      },
      {
          "name":"Ret_Qty_from_DB",
          "description":"Tell a user about the quantity of a product. For instance when a user asks 'How many units of Gaming console is in stock'",
          "parameters":{
              "type":"object",
              "properties":{
                  "ItemName":{
                    "type": "string",
                    "description":"The name of the Item / product",
                  },
              },
              "required":["ItemName"],
              "additionalProperties":False,
          },
      },
      {
          "name":"send_email",
          "description":"Send an email to the address provided. For instance 'Send an email to kojo@gmail.com'",
          "parameters":{
              "type":"object",
              "properties":{
                  "eID":{
                    "type": "string",
                    "description":"The email provided by the user",
                  },
              },
              "required":["Quantity"],
              "required":["ItemName"],
              "additionalProperties":False,
          },
      },
      {
          "name":"forecast_arrival_dates",
          "description":"Outputs a prediction for the next 10 days. For instance: 'What date will a product to be delivered'",
          "parameters":{
              "type":"object",
              "properties":{
                  "product_id":{
                    "type": "string",
                    "description":"The product id / name provided by the user",
                  },
              },
              "required":["product_id"],
              "additionalProperties":False,
          }
      }
  ]

  # if (call_signal == 0):

  #   history_prompt = []
  #   call_signal = 1

  #Assigning User Prompt to current_prompt.
  current_prompt = [HumanMessage(content=user_prompt)]

  #Begin Loop
  while True:
    
    history.add_user_message(user_prompt)
    #response = client.invoke(history.messages)

    #print(history.messages)
    response = client.invoke(
          history.messages,
          #current_prompt,
          functions = function_descriptions
      )    
    history.add_ai_message(response)
    
    history_prompt.append(HumanMessage(content=user_prompt))
    history_prompt.append(AIMessage(content=str(response.content)))
    
    if 'function_call' in response.additional_kwargs:
      #Select the chosen function
      function_chosen = eval(response.additional_kwargs["function_call"]["name"])

      # Access the arguments
      params = json.loads(response.additional_kwargs["function_call"]["arguments"])

      #Execute the chosen function
      result = function_chosen(**params)
      print("The function chosen is")
      print(function_chosen)
      print("And has its parameters as")
      print(params)
      print(result)
      
      print("Response in function call loop")
      print(response)

      #HumanMessage(content=user_prompt),
      current_prompt.append(AIMessage(content=str(response.additional_kwargs)))
      current_prompt.append(AIMessage(
          role="function",
          additional_kwargs={
              "name":response.additional_kwargs["function_call"]["name"]
          },
          content = f"Completed function {function_chosen} execution with the result: {result}"))
      
      # print(current_prompt)
    else:
      break
    
  print(response)
  
  print("Current Prompt")
  print(history.messages)
  print("Final Response")
  print(response.content)
  return response.content