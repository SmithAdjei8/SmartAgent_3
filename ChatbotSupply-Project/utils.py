from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

import numpy as np
import os
import json
import string
import mysql.connector
import pickle

#initialize OPENAI API with Key
os.environ["OPENAI_API_KEY"] = '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'
client = ChatOpenAI(model = "gpt-3.5-turbo-0125", temperature=0)

#Load the model
#model = ARIMAResults.load("/content/arima_model.pkl")

# Function to connect to the database
def DB_Connection(host,user,password,database):
  db = mysql.connector.connect(
      host = host,
      user = user,
      password = password,
      database = database
  )
  return db

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

  #Arrival date prediction here
#   model_features = [ItemName,Quantity]
#   conv_features = [np.array(model_features)]
#   prediction = model.predict(conv_features)

#   return Quantity + "units of " + ItemName + "(s) has been ordered and is estimated to arrive on "+ prediction

# Function to retrieve data from the database
def Ret_Qty_from_DB(ItemName):
  db_connection = DB_Connection("127.0.0.1","root","smartagents_3","SupplyChainInventory")
  print("Database Connection Successful")
  DB_Cursor = db_connection.cursor()

  cmdstring = '''Select 
                sum(case when t.stockin_stockout = TRUE then t.quantitySold else 0 end) - 
                sum(case when t.stockin_stockout = FALSE then t.quantitySold else 0 end) as 'Quantity'
                from Products p left join Transaction_Db t
                on p.ProductID = t.ProductID
                where p.ProductName = %s'''
  val = (ItemName,)

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
          "description":"Send an email to the address provided",
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
      }
  ]

  first_response = client.invoke(
      [HumanMessage(content=user_prompt)],
      functions = function_descriptions
  )
  print("The first response is")
  print(first_response)

  if 'function_call' in first_response.additional_kwargs:
    #Select the chosen function
    function_chosen = eval(first_response.additional_kwargs["function_call"]["name"])

    # Access the arguments
    params = json.loads(first_response.additional_kwargs["function_call"]["arguments"])

    #Execute the chosen function
    result = function_chosen(**params)
    print("The function chosen is")
    print(function_chosen)
    print("And has its parameters as")
    print(params)
    print(result)

    second_response = client.invoke(
        [
          HumanMessage(content=user_prompt),
          AIMessage(content=str(first_response.additional_kwargs)),
          AIMessage(
              role="function",
              additional_kwargs={
                  "name":first_response.additional_kwargs["function_call"]["name"]
              },
              content = f"Completed function {function_chosen} execution with the result: {result}",
          ),
        ],
        functions=function_descriptions,
    )
    print('')
    print("The second response is")
    print(second_response)

    if 'function_call' in second_response.additional_kwargs:
      #Select the chosen function
      second_function_chosen = eval(second_response.additional_kwargs["function_call"]["name"])

      # Access the arguments
      params = json.loads(second_response.additional_kwargs["function_call"]["arguments"])

      #Execute the chosen function
      result = second_function_chosen(**params)
      print("The second function chosen is")
      print(second_function_chosen)
      print("And has its parameters as")
      print(params)
      print(result)

      third_response = client.invoke(
        [
          HumanMessage(content=user_prompt),
          AIMessage(content=str(first_response.additional_kwargs)),
          AIMessage(content=str(second_response.additional_kwargs)),
          AIMessage(
              role="function",
              additional_kwargs={
                  "name":second_response.additional_kwargs["function_call"]["name"]
              },
              content =  f"Completed function {function_chosen} execution with the result: {result}",
          ),
        ],
        functions=function_descriptions,
    )
      
      print('')
      print("The third response is")
      print(third_response)
      
      if 'function_call' in third_response.additional_kwargs:

        #Select the chosen function
        third_function_chosen = eval(third_response.additional_kwargs["function_call"]["name"])

        # Access the arguments
        params = json.loads(third_response.additional_kwargs["function_call"]["arguments"])

        #Execute the chosen function
        result = third_function_chosen(**params)
        print("The third function chosen is")
        print(third_function_chosen)
        print("And has its parameters as")
        print(params)
        print(result)

        fourth_response = client.invoke(
          [
            HumanMessage(content=user_prompt),
            AIMessage(content=str(first_response.additional_kwargs)),
            AIMessage(content=str(second_response.additional_kwargs)),
            AIMessage(content=str(third_response.additional_kwargs)),
            AIMessage(
                role="function",
                additional_kwargs={
                    "name":third_response.additional_kwargs["function_call"]["name"]
                },
                content =  f"Completed function {function_chosen} execution with the result: {result}",
            ),
          ],
          functions=function_descriptions,
      )
        
        print('')
        print("The fourth response is")
        print(fourth_response)
        return fourth_response.content

      return third_response.content

    return second_response.content

  return first_response.content