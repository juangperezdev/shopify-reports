from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
from datetime import datetime
from main import generate_report_for_date

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para flash messages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    target_date = request.form.get('date')
    
    if not target_date:
        flash('Por favor selecciona una fecha', 'error')
        return redirect(url_for('index'))
    
    try:
        # Validar formato de fecha
        datetime.strptime(target_date, '%Y-%m-%d')
        
        # Generar reporte
        filename = generate_report_for_date(target_date)
        
        if filename and os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            flash('No se pudo generar el reporte. Verifica que haya datos para esa fecha.', 'error')
            return redirect(url_for('index'))
            
    except ValueError:
        flash('Formato de fecha inválido', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
