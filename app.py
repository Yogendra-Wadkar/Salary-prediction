from flask import Flask, request, jsonify, render_template
import pickle
import numpy as np

app = Flask(__name__)

with open('salary_model.pkl', 'rb') as f:
    bundle = pickle.load(f)

model = bundle['model']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        d = request.get_json()
        row = [[
            int(d['work_year']),
            int(d['experience_level']),
            int(d['employment_type']),
            int(d['job_title']),
            int(d['salary_currency']),
            float(d['salary_in_usd']),
            int(d['employee_residence']),
            int(d['remote_ratio']),
            int(d['company_location']),
            int(d['company_size'])
        ]]
        pred = model.predict(row)[0]
        return jsonify({'predicted_salary': round(float(pred), 2), 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 400

if __name__ == '__main__':
    app.run(debug=True)
