import os
import logging
import json
import csv
from datetime import datetime
from io import StringIO, BytesIO
from flask import Flask, render_template, request, jsonify, Response
from enhanced_collectors import WorldBankCollector, IMFCollector, USAIDCollector, UNCollector, AfricanDevelopmentBankCollector, ZambianStatisticsCollector
from email_service import EmailService

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize data collectors
wb_collector = WorldBankCollector()
imf_collector = IMFCollector()
usaid_collector = USAIDCollector()
un_collector = UNCollector()
afdb_collector = AfricanDevelopmentBankCollector()
zambian_stats_collector = ZambianStatisticsCollector()

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
        elif source == 'afdb':
            result = afdb_collector.collect_data(data_type)
        elif source == 'zambian_stats':
            result = zambian_stats_collector.collect_data(data_type)
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
    """Generate and download data file based on format"""
    try:
        data = request.get_json()
        records = data.get('data', [])
        source = data.get('source', 'Unknown')
        data_type = data.get('data_type', 'Unknown')
        file_format = data.get('format', 'csv')
        
        if not records:
            return jsonify({'error': 'No data provided for download'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if file_format == 'json':
            # JSON export
            json_data = {
                'metadata': {
                    'source': source,
                    'data_type': data_type,
                    'generated_date': datetime.now().isoformat(),
                    'total_records': len(records)
                },
                'data': records
            }
            
            filename = f"zambia_{source.replace(' ', '_')}_{data_type}_{timestamp}.json"
            
            return Response(
                json.dumps(json_data, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
        
        elif file_format == 'excel':
            # Try Excel export with pandas
            try:
                import pandas as pd
                from io import BytesIO
                
                # Create DataFrame
                df = pd.DataFrame(records)
                
                # Create Excel file in memory
                output = BytesIO()
                
                # Create Excel writer
                writer = pd.ExcelWriter(output, engine='openpyxl')
                
                # Write main data
                df.to_excel(writer, sheet_name='Zambia Data', index=False)
                
                # Add metadata sheet
                metadata_data = [
                    ['Source', source],
                    ['Data Type', data_type],
                    ['Generated Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['Total Records', len(records)]
                ]
                metadata_df = pd.DataFrame(metadata_data, columns=['Field', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
                
                # Close writer
                writer.close()
                
                output.seek(0)
                filename = f"zambia_{source.replace(' ', '_')}_{data_type}_{timestamp}.xlsx"
                
                return Response(
                    output.getvalue(),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )
                
            except ImportError:
                # Fallback to CSV if pandas not available
                file_format = 'csv'
        
        # Default CSV export
        output = StringIO()
        
        if records:
            # Get all unique headers from all records
            all_headers = set()
            for record in records:
                all_headers.update(record.keys())
            
            headers = sorted(list(all_headers))
            
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(headers)
            
            # Write metadata row
            writer.writerow([])
            writer.writerow(['# Metadata'])
            writer.writerow(['Source:', source])
            writer.writerow(['Data Type:', data_type])
            writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Total Records:', len(records)])
            writer.writerow([])
            writer.writerow(['# Data'])
            writer.writerow(headers)
            
            # Add data rows
            for record in records:
                row = [str(record.get(header, '')) for header in headers]
                writer.writerow(row)
        
        # Convert to string
        csv_content = output.getvalue()
        
        # Generate filename
        filename = f"zambia_{source.replace(' ', '_')}_{data_type}_{timestamp}.csv"
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        logging.error(f"Error in download: {str(e)}")
        return jsonify({'error': f'File generation failed: {str(e)}'}), 500

@app.route('/send_email', methods=['POST'])
def send_email():
    """Send fetched data via email"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get email parameters
        to_email = data.get('email')
        records = data.get('data', [])
        source = data.get('source', 'Unknown')
        data_type = data.get('data_type', 'Various')
        format_type = data.get('format', 'csv')
        
        if not to_email:
            return jsonify({"error": "Email address is required"}), 400
        
        if not records:
            return jsonify({"error": "No data to send"}), 400
        
        # Prepare metadata
        metadata = {
            'source': source,
            'data_type': data_type,
            'total_records': len(records),
            'generated_at': datetime.now().isoformat()
        }
        
        # Send email
        email_service = EmailService()
        result = email_service.send_data_report(to_email, records, metadata, format_type)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": f"Data report sent successfully to {to_email}"
            })
        else:
            return jsonify({
                "error": f"Failed to send email: {result['error']}"
            }), 500
        
    except Exception as e:
        logging.error(f"Email sending error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)