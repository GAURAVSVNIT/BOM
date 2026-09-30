"""
Anjani Interweave — U-Panel FIBC BOM Generator
Run:  python3 app.py
Open: http://localhost:5000
"""

import io
import csv
import json
from flask import Flask, render_template, request, jsonify, make_response
from bom_engine import generate_bom, select_body_gsm, select_loop_gsm, LOOM_WIDTHS

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', loom_widths=LOOM_WIDTHS)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json()
    try:
        result = generate_bom(data)
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/suggest_gsm', methods=['POST'])
def api_suggest_gsm():
    d = request.get_json()
    swl = float(d.get('swl_kg', 1000))
    sf  = float(d.get('sf', 5))
    lam = bool(d.get('body_laminated', True))
    dl  = bool(d.get('double_layer', False))
    gsm = select_body_gsm(swl, sf, lam, dl)
    lgm = select_loop_gsm(swl, sf)
    return jsonify({'gsm': gsm, 'loop_gsm': lgm,
                    'design_load': swl * sf})


@app.route('/api/export_csv', methods=['POST'])
def export_csv():
    data = request.get_json()
    result = generate_bom(data)
    comps = result['components']

    output = io.StringIO()
    writer = csv.writer(output)

    # Header info
    spec = result['spec']
    writer.writerow(['ANJANI INTERWEAVE PVT LTD — BILL OF MATERIAL'])
    writer.writerow([])
    writer.writerow(['SWL (KG)', spec['swl_kg'], 'SF', spec['sf'],
                     'DESIGN LOAD', result['design_load_kg']])
    writer.writerow(['BAG SIZE (INT)', f"{spec['int_L']}×{spec['int_W']}×{spec['int_H']} cm",
                     'BAG SIZE (EXT)', f"{spec.get('ext_L','-')}×{spec.get('ext_W','-')}×{spec.get('ext_H','-')} cm"])
    writer.writerow(['BODY GSM (AUTO)', result['gsm_auto'],
                     'EST. BAG WT.', f"{result['est_bag_wt_kg']} KG",
                     'VOLUME', f"{result['volume_m3']} m³"])
    writer.writerow([])

    # Component table
    writer.writerow(['SR', 'COMPONENT', 'GSM', 'LAMI/UL', 'COLOR',
                     'FABRIC WIDTH (CM)', 'CUT LENGTH (CM)', 'CUT WT (G)', 'QTY', 'REMARK'])
    for c in comps:
        writer.writerow([
            c.get('sr', ''), c.get('component', ''), c.get('gsm', ''),
            c.get('lami_ul', ''), c.get('color', ''),
            c.get('fw', ''), c.get('cut', ''),
            c.get('weight_g', ''), c.get('qty', ''), c.get('remark', '')
        ])
    writer.writerow([])
    writer.writerow(['', '', '', '', '', '', 'GRAND TOTAL (g)', result['fabric_total_g']])
    writer.writerow(['', '', '', '', '', '', 'EST. BAG WT. (kg)', result['est_bag_wt_kg']])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=BOM_Anjani.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  Anjani Interweave — U-Panel BOM Generator")
    print("  Open your browser at: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=False, port=5000)
