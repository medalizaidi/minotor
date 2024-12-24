

# Importing required libraries and modules
from bson import ObjectId
from flask import Flask, jsonify, request, send_file
from pymongo import MongoClient
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from dotenv import load_dotenv
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt

# Load environment variables from .env file
load_dotenv()



# Initialize Flask app
app = Flask(__name__)

# Enable CORS for specific routes
CORS(app, resources={
    r"/add": {"origins": "http://localhost:3039"},
    r"/get": {"origins": "http://localhost:3039"},
    r"/export-native-shift-pdf/*": {"origins": "http://localhost:3039"},
    r"/export-monthly-pdf/*": {"origins": "http://localhost:3039"},
    r"/delete/*": {"origins": "http://localhost:3039"},
    r"/get/*": {"origins": "http://localhost:3039"},
    r"/update/*": {"origins": "http://localhost:3039"},
})

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.mydatabase
metrics_collection = db.system_metrics  
daily_max_collection = db.daily_max_metrics 
incident_collection = db.incidents


############################################
############### API'S and ENDPOINT#########
#########################################



# Route to add data
@app.route("/add", methods=["POST"])
def add_data():
    data = request.json  
    if not data:
        return jsonify({"error": "Invalid data provided"}), 400  

    metrics_collection.insert_one(data)  

    date = data.get("date")
    shift_count = metrics_collection.count_documents({"date": date})
    if shift_count == 3:
        calculate_and_store_max_metrics(date)

    return jsonify({"message": "Data inserted successfully!"}), 201

# Set logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)

# Route to retrieve all metrics data
@app.route("/get", methods=["GET"])
def get_all_data():
    data = list(metrics_collection.find({}, {"_id": 0}))  
    return jsonify(data)

# Route to retrieve metrics data by date and shift
@app.route("/get/<string:date>/<int:shift>", methods=["GET"])
def get_data_by_shift(date, shift):
    data = metrics_collection.find_one({"date": date, "shift": shift}, {"_id": 0})
    if not data:
        return jsonify({"error": "No data found for the given date and shift"}), 404
    return jsonify(data)

# Route to get the maximum metrics data for a given date
@app.route("/get-daily-max/<string:date>", methods=["GET"])
def get_daily_max(date):
    calculate_and_store_max_metrics(date)    
    max_metrics = daily_max_collection.find_one({"date": date}, {"_id": 0})
    if not max_metrics:
        return jsonify({"error": f"No max metrics found for the given date: {date}"}), 404
    return jsonify(max_metrics)

# Route to export data for a specific shift into a PDF
@app.route("/export-native-shift-pdf/<string:date>/<int:shift>", methods=["GET"])
def export_by_shift_pdf(date, shift):
    data = metrics_collection.find_one({"date": date, "shift": shift}, {"_id": 0})
    if not data:
        return jsonify({"error": f"No data found for the given date: {date} and shift: {shift}"}), 404
    
    file_name = f"shift_output/AKS Daily Monitoring Report_{date}_{shift}.pdf"
    create_daily_max_pdf(date, data, "./avaxia-logo.png", output_file=file_name)

    return send_file(file_name, as_attachment=True)

# Route to export the daily maximum metrics data into a PDF
@app.route("/export-pdf/<string:date>", methods=["GET"])
def export_daily_max_pdf(date):
    data = daily_max_collection.find_one({"date": date}, {"_id": 0})
    if not data:
        return jsonify({"error": "No data found for the given date"}), 404

    file_name = f"daily_output/{date}_daily_max_report.pdf"
    create_daily_max_pdf(date, data, "./avaxia-logo.png", output_file=file_name)

    return send_file(file_name, as_attachment=True)

# Route to send an email with the report attached for max_daily
@app.route("/send-email/<string:date>", methods=["POST"])
def send_email(date):
  
    try:
        recipient_email = "laytharfaoui48@gmail.com"
        pdf_path = f"daily_output/AKS Daily Monitoring Report_{date}_{shift}.pdf"

        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASS = os.getenv("EMAIL_PASS")

        if not EMAIL_USER or not EMAIL_PASS:
            return jsonify({"error": "Email credentials are not set!"}), 400

        subject = f"Daily Metrics for {date}"

        message = MIMEMultipart()
        message["From"] = EMAIL_USER
        message["To"] = recipient_email
        message["Subject"] = subject

        body = "Hello team,\n\nPlease find the attached report of the PTO project.\n\nBest regards."
        message.attach(MIMEText(body, "plain"))

        # Attach the PDF
        try:
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={pdf_path}")
                message.attach(part)
        except FileNotFoundError:
            return jsonify({"error": f"Attachment file '{pdf_path}' not found."}), 400

        # Connect to the SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, recipient_email, message.as_string())

        return jsonify({"message": "Email sent successfully!"})
    
    except smtplib.SMTPAuthenticationError as e:
        return jsonify({"error": "SMTP Authentication Error. Check your credentials or App Password.", "details": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

# send an email with the raport of shift attached
@app.route("/send-email/<string:date>/<int:shift>", methods=["POST"])
def send_email_shift(date , shift):
  
    try:
        recipient_email = "laytharfaoui48@gmail.com"
        pdf_path = f"shift_output/AKS Daily Monitoring Report_{date}_{shift}.pdf"

        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASS = os.getenv("EMAIL_PASS")

        if not EMAIL_USER or not EMAIL_PASS:
            return jsonify({"error": "Email credentials are not set!"}), 400

        subject = f"Daily Metrics for {date}"

        message = MIMEMultipart()
        message["From"] = EMAIL_USER
        message["To"] = recipient_email
        message["Subject"] = subject

        body = "Hello team,\n\nPlease find the attached report of the PTO project.\n\nBest regards."
        message.attach(MIMEText(body, "plain"))

        # Attach the PDF
        try:
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={pdf_path}")
                message.attach(part)
        except FileNotFoundError:
            return jsonify({"error": f"Attachment file '{pdf_path}' not found."}), 400

        # Connect to the SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, recipient_email, message.as_string())

        return jsonify({"message": "Email sent successfully!"})
    
    except smtplib.SMTPAuthenticationError as e:
        return jsonify({"error": "SMTP Authentication Error. Check your credentials or App Password.", "details": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

# Route to update shift data
@app.route("/update/<string:date>/<int:shift>", methods=["PUT"])
def update_shift_data(date, shift):
    updated_data = request.json
    if not updated_data:
        return jsonify({"error": "Invalid data provided"}), 400
    result = metrics_collection.update_one({"date": date, "shift": shift}, {"$set": updated_data})
    if result.matched_count == 0:
        return jsonify({"error": "No data found to update for the given date and shift"}), 404
    return jsonify({"message": "Data updated successfully!"})

# Route to delete shift data
@app.route("/delete/<string:date>/<int:shift>", methods=["DELETE"])
def delete_shift_data(date, shift):
    result = metrics_collection.delete_one({"date": date, "shift": shift})
    if result.deleted_count == 0:
        return jsonify({"error": "No data found to delete for the given date and shift"}), 404
    return jsonify({"message": "Data deleted successfully!"})

# Route to retrieve daily metrics table
@app.route("/get-daily-table", methods=["GET"])
def get_daily_table():
    table = generate_daily_table()
    if not table:
        return jsonify({"error": "No daily metrics data available"}), 404
    return jsonify(table)
########

@app.route("/export-monthly-pdf-with-charts-separate-pages/<int:year>/<int:month>", methods=["GET"])
def export_monthly_report_pdf_with_charts_separate_pages(year, month):
    # Generate daily table data
    daily_table = generate_daily_table()

    # Filter data for the specified month and year
    monthly_data = {}
    for component, entries in daily_table.items():
        monthly_entries = [
            entry for entry in entries
            if datetime.strptime(entry["date"], "%d-%m-%Y").month == month and
               datetime.strptime(entry["date"], "%d-%m-%Y").year == year
        ]
        if monthly_entries:
            monthly_data[component] = monthly_entries

    if not monthly_data:
        return jsonify({"error": "No data found for the specified month and year."}), 404

    # Create the PDF with charts on separate pages
    file_name = f"monthly_output/monthly_report_with_charts_separate_pages_{month}_{year}.pdf"
    create_monthly_report_pdf_with_charts_separate_pages(month, year, monthly_data, "./avaxia-logo.png", output_file=file_name)

    # Send the PDF file
    return send_file(file_name, as_attachment=True)

@app.route("/get-all-daily-max", methods=["GET"])
def get_all_daily_max():
    max_daily_data = get_all_max_daily()
    if not max_daily_data:
        return jsonify({"error": "No max_daily metrics data available or an error occurred."}), 500
    return jsonify(max_daily_data)

@app.route("/get-all-monthly", methods=["GET"])
def get_all_monthly_data():
    monthly_data = get_all_monthly()
    if not monthly_data:
        return jsonify({"error": "No monthly data available or an error occurred."}), 500
    return jsonify(monthly_data)

@app.route("/usage", methods=["GET"])
def get_usage_by_period_and_component():
    # Get query parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    component = request.args.get("component")

    if not (start_date and end_date and component):
        return jsonify({"error": "Missing required query parameters: start_date, end_date, or component"}), 400

    try:
        # Parse and validate date format
        start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
        end_date_obj = datetime.strptime(end_date, "%d-%m-%Y")

        # Extract day, month, and year from start and end dates
        start_day, start_month, start_year = start_date_obj.day, start_date_obj.month, start_date_obj.year
        end_day, end_month, end_year = end_date_obj.day, end_date_obj.month, end_date_obj.year

        # Query daily_max_collection for the specified period
        pipeline = [
            {
                "$addFields": {  # Extract day, month, and year from the date string
                    "day": {"$toInt": {"$substr": ["$date", 0, 2]}},
                    "month": {"$toInt": {"$substr": ["$date", 3, 2]}},
                    "year": {"$toInt": {"$substr": ["$date", 6, 4]}},
                }
            },
            {
                "$match": {
                    "$and": [
                        {"year": {"$gte": start_year, "$lte": end_year}},
                        {"month": {"$gte": start_month, "$lte": end_month}},
                        {"day": {"$gte": start_day, "$lte": end_day}}
                    ]
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": 1,
                    f"cpu_usage.{component}": 1,
                    f"memory_usage.{component}": 1
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "cpu_usage": {"$max": f"$cpu_usage.{component}"},
                    "memory_usage": {"$max": f"$memory_usage.{component}"}
                }
            },
            {
                "$sort": {"_id": 1}  # Sort by date
            }
        ]

        usage_data = list(daily_max_collection.aggregate(pipeline))

        # Format the response
        response = [
            {
                "date": entry["_id"],
                "cpu_usage": entry["cpu_usage"] if entry["cpu_usage"] is not None else "Not Available",
                "memory_usage": entry["memory_usage"] if entry["memory_usage"] is not None else "Not Available"
            }
            for entry in usage_data
        ]

        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": f"Invalid date format. Expected 'dd-mm-yyyy'. Details: {str(e)}"}), 400
    except Exception as e:
        logging.error(f"Error fetching usage data: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
#################################
##########incident-part##########
#################################

# 1. Create Incident
@app.route("/incidents", methods=["POST"])
def create_incident():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data provided"}), 400

    # Insert the incident into the collection
    incident_id = incident_collection.insert_one(data).inserted_id
    return jsonify({"message": "Incident created successfully!", "id": str(incident_id)}), 201

# 2. Retrieve All Incidents
@app.route("/incidents", methods=["GET"])
def get_all_incidents():
    incidents = list(incident_collection.find({}))
    for incident in incidents:
        # Convert MongoDB's _id to a string and rename it to "id"
        incident["id"] = str(incident.pop("_id"))
    return jsonify(incidents), 200
# 3. Retrieve Incident by ID
@app.route("/incidents/<string:incident_id>", methods=["GET"])
def get_incident_by_id(incident_id):
    incident = incident_collection.find_one({"_id": ObjectId(incident_id)}, {"_id": 0})
    if not incident:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify(incident)

# 4. Update Incident by ID
@app.route("/incidents/<string:incident_id>", methods=["PUT"])
def update_incident(incident_id):
    updated_data = request.json
    if not updated_data:
        return jsonify({"error": "Invalid data provided"}), 400

    result = incident_collection.update_one({"_id": ObjectId(incident_id)}, {"$set": updated_data})
    if result.matched_count == 0:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify({"message": "Incident updated successfully!"})

# 5. Delete Incident by ID
@app.route("/incidents/<string:incident_id>", methods=["DELETE"])
def delete_incident(incident_id):
    result = incident_collection.delete_one({"_id": ObjectId(incident_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify({"message": "Incident deleted successfully!"})



#########################
#### ALL FUNCTION #######
#########################



# Function to calculate and store daily maximum 
def calculate_and_store_max_metrics(date):
    shifts = list(metrics_collection.find({"date": date}))
    logging.debug(f"Shifts for {date}: {shifts}")

    if len(shifts) < 3:
        logging.error(f"Not enough shifts for {date}. Expected 3, found {len(shifts)}.")
        return

    max_cpu = {}
    max_memory = {}
    application_availability = {}

    for shift in shifts:
        cpu_usage = shift.get("cpu_usage", {})
        memory_usage = shift.get("memory_usage", {})
        app_avail = shift.get("Application_Availability", {})

        for key, value in cpu_usage.items():
            if isinstance(value, (int, float)):
                if key not in max_cpu or value > max_cpu[key]:
                    max_cpu[key] = value
            elif key == "sbp-be" and value == "down":
                max_cpu[key] = "Down"

        for key, value in memory_usage.items():
            if isinstance(value, (int, float)):
                if key not in max_memory or value > max_memory[key]:
                    max_memory[key] = value
            elif key == "sbp-be" and value == "down":
                max_memory[key] = "Down"

        for key, value in app_avail.items():
            if key not in application_availability:
                application_availability[key] = value

    max_metrics = {
        "date": date,
        "cpu_usage": max_cpu,
        "memory_usage": max_memory,
        "application_availability": application_availability,
    }

    # Update the daily_max_collection
    daily_max_collection.update_one(
        {"date": date}, {"$set": max_metrics}, upsert=True
    )
    logging.debug(f"Updated max metrics: {max_metrics}")
# Function to create daily/shift PDF report
def create_daily_max_pdf(date, max_data, header_image_path, output_file="daily_max_report.pdf"):
    class PDF(FPDF):
        def header(self):
            self.image(header_image_path, x=10, y=-12, w=190)
            self.ln(20)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Date: {date}", ln=True, align="C")
    pdf.ln(10)

    # Organizational Applications Section
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Organizational Applications: PTO", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=12)

    pdf.cell(60, 10, "Component", 1, 0, "C")
    pdf.cell(40, 10, "CPU Usage (core)", 1, 0, "C")
    pdf.cell(50, 10, "Memory Usage", 1, 0, "C")
    pdf.cell(45, 10, "Availability (%)", 1, 1, "C")

    # List of organizational components, including sbp-fe
    organizational_components = ["blc-be", "blc-fe", "gco-be", "gco-fe", "sbp-be", "sbp-fe"]
    for component in organizational_components:
        cpu = max_data["cpu_usage"].get(component, "Not Available")
        memory = max_data["memory_usage"].get(component, "Not Available")
        availability = "100%" if component != "sbp-be" and cpu != "Down" else "Down"
        
        # Remove "MiB" if the memory value is "Down" or non-numeric
        memory_display = f"{memory} MiB" if isinstance(memory, (int, float)) else memory

        pdf.cell(60, 10, component, 1, 0, "C")
        pdf.cell(40, 10, str(cpu), 1, 0, "C")
        pdf.cell(50, 10, memory_display, 1, 0, "C")
        pdf.cell(45, 10, availability, 1, 1, "C")

    pdf.ln(10)

    # Tools Section
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Tools:", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=12)

    pdf.cell(65, 10, "Component", 1, 0, "C")
    pdf.cell(40, 10, "CPU Usage (core)", 1, 0, "C")
    pdf.cell(50, 10, "Memory Usage", 1, 0, "C")
    pdf.cell(40, 10, "Availability (%)", 1, 1, "C")

    # Add components to Tools section excluding the ones in organizational_components
    for component in max_data["cpu_usage"]:
        if component not in organizational_components:
            cpu = max_data["cpu_usage"].get(component, "Not Available")
            memory = max_data["memory_usage"].get(component, "Not Available")
            availability = "100%" if cpu != "Down" else "Down"

            # Remove "MiB" if the memory value is "Down" or non-numeric
            memory_display = f"{memory} MiB" if isinstance(memory, (int, float)) else memory

            pdf.cell(65, 10, component, 1, 0, "C")
            pdf.cell(40, 10, str(cpu), 1, 0, "C")
            pdf.cell(50, 10, memory_display, 1, 0, "C")
            pdf.cell(40, 10, availability, 1, 1, "C")

    pdf.output(output_file)  
    return output_file
# Function to create monthly report PDF
def create_monthly_report_pdf_with_charts_separate_pages(month, year, data, header_image_path, output_file="monthly_report.pdf", charts_folder="charts"):
    class PDF(FPDF):
        def header(self):
            self.image(header_image_path, x=10, y=-8, w=190)
            self.ln(30)
            if self.page_no() == 1:  # Add header only on the first page
                self.set_font("Arial", "B", 20)
                self.cell(0, 10, "Monthly Report", 0, 1, "C")
                self.ln(5)

        def footer(self):
            self.rect(5, 5, 200, 287)
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    # Ensure the charts folder exists
    if not os.path.exists(charts_folder):
        os.makedirs(charts_folder)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add the first page with title
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Metrics for {month}-{year}", ln=True, align="C")
    pdf.ln(20)  # Add more spacing for aesthetics

    # Iterate over components
    for component, entries in data.items():
        # Add a new page for the table
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Component: {component}", ln=True)
        pdf.set_font("Arial", size=10)

        # Table header
        pdf.cell(40, 10, "Date", 1, 0, "C")
        pdf.cell(40, 10, "CPU Usage (core)", 1, 0, "C")
        pdf.cell(50, 10, "Memory Usage (MiB)", 1, 0, "C")
        pdf.cell(50, 10, "Availability (%)", 1, 1, "C")

        # Table rows
        for entry in entries:
            pdf.cell(40, 10, entry["date"], 1, 0, "C")
            pdf.cell(40, 10, str(entry["cpu_usage"]), 1, 0, "C")
            pdf.cell(50, 10, str(entry["memory_usage"]), 1, 0, "C")
            pdf.cell(50, 10, str(entry["availability"]), 1, 1, "C")

        pdf.ln(5)  # Add space after the table

        # Generate charts for the component
        cpu_chart_file, memory_chart_file = generate_component_charts(component, entries, charts_folder)

        # Add a new page for the charts
        pdf.add_page()

        # Add CPU chart
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, f"CPU Usage Chart for {component}", ln=True, align="C")
        pdf.image(cpu_chart_file, x=20, y=40, w=170, h=90)

        # Add Memory chart
        pdf.ln(95)  # Move below the first chart
        pdf.cell(0, 10, f"Memory Usage Chart for {component}", ln=True, align="C")
        pdf.image(memory_chart_file, x=20, y=140, w=170, h=90)

    # Save PDF
    pdf.output(output_file)
    return output_file
# Function to generate charts for the monthly
def generate_component_charts(component, entries, charts_folder):
    dates = [entry["date"] for entry in entries]
    cpu_usage = [entry["cpu_usage"] if isinstance(entry["cpu_usage"], (int, float)) else 0 for entry in entries]
    memory_usage = [entry["memory_usage"] if isinstance(entry["memory_usage"], (int, float)) else 0 for entry in entries]

    # CPU Usage Chart
    plt.figure(figsize=(10, 5))
    plt.plot(dates, cpu_usage, marker="o", label="CPU Usage (core)")
    plt.title(f"CPU Usage for {component}")
    plt.xlabel("Date")
    plt.ylabel("CPU Usage (core)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    cpu_chart_file = os.path.join(charts_folder, f"{component}_cpu_chart.png")
    plt.savefig(cpu_chart_file)
    plt.close()

    # Memory Usage Chart
    plt.figure(figsize=(10, 5))
    plt.plot(dates, memory_usage, marker="o", label="Memory Usage (MiB)", color="orange")
    plt.title(f"Memory Usage for {component}")
    plt.xlabel("Date")
    plt.ylabel("Memory Usage (MiB)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    memory_chart_file = os.path.join(charts_folder, f"{component}_memory_chart.png")
    plt.savefig(memory_chart_file)
    plt.close()

    return cpu_chart_file, memory_chart_file# generate table for component of the dailys
def generate_daily_table():
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "date": 1,
                "cpu_usage": 1,
                "memory_usage": 1,
                "application_availability": 1
            }
        },
        {"$sort": {"date": 1}}  # Sort by date
    ]

    daily_data = list(daily_max_collection.aggregate(pipeline))

    table = {}
    seen_dates = {}

    for entry in daily_data:
        date = entry["date"]
        cpu_usage = entry.get("cpu_usage", {})
        memory_usage = entry.get("memory_usage", {})
        availability = entry.get("application_availability", {})

        for component in set(cpu_usage.keys()).union(memory_usage.keys()).union(availability.keys()):
            if component not in table:
                table[component] = []
                seen_dates[component] = set()

            if date not in seen_dates[component]:
                table[component].append({
                    "date": date,
                    "cpu_usage": cpu_usage.get(component, "Down" if component == "sbp-be" else "Not Available"),
                    "memory_usage": memory_usage.get(component, "Down" if component == "sbp-be" else "Not Available"),
                    "availability": availability.get(component, "Down" if component == "sbp-be" else "Not Available"),
                })
                seen_dates[component].add(date)

    return table
def get_all_max_daily():
    try:
        # Fetch all documents from daily_max_collection
        max_daily_data = list(daily_max_collection.find({}, {"_id": 0}))  # Exclude MongoDB's `_id` field
        return max_daily_data
    except Exception as e:
        logging.error(f"Error fetching max_daily data: {e}")
        return None
def get_all_monthly():
    try:
        # Aggregate daily max data grouped by month
        pipeline = [
            {
                "$project": {
                    "_id": 0,
                    "date": 1,
                    "cpu_usage": 1,
                    "memory_usage": 1,
                    "application_availability": 1,
                    "year": {"$year": {"$dateFromString": {"dateString": "$date", "format": "%d-%m-%Y"}}},
                    "month": {"$month": {"$dateFromString": {"dateString": "$date", "format": "%d-%m-%Y"}}}
                }
            },
            {
                "$group": {
                    "_id": {"year": "$year", "month": "$month"},
                    "days": {"$push": {"date": "$date", "cpu_usage": "$cpu_usage", "memory_usage": "$memory_usage", "application_availability": "$application_availability"}}
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1}}  # Sort by year and month
        ]

        # Fetch data
        monthly_data = list(daily_max_collection.aggregate(pipeline))

        # Format the response
        result = [
            {
                "year": item["_id"]["year"],
                "month": item["_id"]["month"],
                "data": item["days"]
            }
            for item in monthly_data
        ]

        return result
    except Exception as e:
        logging.error(f"Error fetching monthly data: {e}")
        return None

# Run the app in debug mode
if __name__ == "__main__":
    HOST = os.getenv("HOST")
    PORT = os.getenv("PORT")
    app.run(host=HOST, port=PORT)
