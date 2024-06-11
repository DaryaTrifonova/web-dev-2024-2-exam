# import io
# from flask import render_template, Blueprint, request, send_file
# from flask_login import current_user, login_required
# from app import db, app
# from math import ceil
# from auth import check_rights, init_login_manager
# PER_PAGE = 10

# bp = Blueprint('visits', __name__, url_prefix='/visits')

# def generate_report_file(records, fields):
#     csv_content = '№,' + ','.join(fields) + '\n'
#     for i, record in enumerate(records):
#         values = [str(getattr(record, f, '')) for f in fields]
#         csv_content += f'{i+1},' + ','.join(values) + '\n'
#     f = io.BytesIO()
#     f.write(csv_content.encode('utf-8'))
#     f.seek(0)
#     return f


