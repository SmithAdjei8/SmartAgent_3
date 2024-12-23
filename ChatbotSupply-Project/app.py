from flask import Flask, render_template, request, jsonify
from utils import asksingle_langchain_ai_agent

import os
import json
import string
import mysql.connector

app = Flask(__name__)


@app.route("/")
def AIAssistant():
    return render_template('Assistant.html')

@app.route("/get", methods=["GET", "POST"])
def AIChat():
    try:
        msg = request.form["msg"]
        input = msg
        primer = f"""
                You are an intelligent Assistant
            """
        
        response = asksingle_langchain_ai_agent(primer,input)
        return jsonify({"response":response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if(__name__) == "__main__":
    app.run(debug=True)