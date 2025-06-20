import os
import logging
import json
from flask import Flask, render_template, request, jsonify, Response
from io import BytesIO
from data_collectors import WorldBankCollector, IMFCollector, USAIDCollector, UNCollector

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize data collectors
wb_collector = WorldBankCollector()
imf_collector = IMFCollector()
usaid_collector = USAIDCollector()
un_collector = UNCollector()

@app.route('/')
def index():
    """Main page with data source and type selection"""
    return render_template('index.html')

@app.route('/api/fetch_data', methods=['POST'])
def fetch_data():
    """API endpoint to fetch data based on source and type"""
    try:
        data = request.get_json()
        source = data.get('source')
        data_type = data.get('data_type')
        
        if not source or not data_type:
            return jsonify({'error': 'Missing source or data_type parameter'}), 400
        
        # Route to appropriate collector
        if source == 'world_bank':
            result = wb_collector.collect_data(data_type)
        elif source == 'imf':
            result = imf_collector.collect_data(data_type)
        elif source == 'usaid':
            result = usaid_collector.collect_data(data_type)
        elif source == 'un':
            result = un_collector.collect_data(data_type)
        else:
            return jsonify({'error': 'Invalid data source'}), 400
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],
                'metadata': result.get('metadata', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in fetch_data: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/download_excel', methods=['POST'])
def download_excel():
    """Generate and download Excel file from provided data"""
    try:
        data = request.get_json()
        records = data.get('data', [])
        source = data.get('source', 'Unknown')
        data_type = data.get('data_type', 'Unknown')
        
        if not records:
            return jsonify({'error': 'No data provided for Excel generation'}), 400
        
        # Import pandas here to avoid startup issues
        try:
            import pandas as pd
            from datetime import datetime
            
            # Create DataFrame
            df = pd.DataFrame(records)
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Zambia Data', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame([
                    ['Source', source],
                    ['Data Type', data_type],
                    ['Generated Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['Total Records', len(records)]
                ], columns=['Field', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            output.seek(0)
            
            # Generate filename
            filename = f"zambia_{source}_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            from flask import send_file
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except ImportError as ie:
            logging.error(f"Pandas import error: {str(ie)}")
            # Fallback to CSV export
            import csv
            from datetime import datetime
            
            output = BytesIO()
            
            # Create CSV content
            csv_content = []
            if records:
                # Get headers from first record
                headers = list(records[0].keys())
                csv_content.append(','.join(headers))
                
                # Add data rows
                for record in records:
                    row = [str(record.get(header, '')) for header in headers]
                    csv_content.append(','.join(row))
            
            csv_string = '\n'.join(csv_content)
            output.write(csv_string.encode('utf-8'))
            output.seek(0)
            
            filename = f"zambia_{source}_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
        
    except Exception as e:
        logging.error(f"Error in download_excel: {str(e)}")
        return jsonify({'error': f'Excel generation failed: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500
