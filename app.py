from flask import Flask, render_template, request
import csv
import io

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        original_file = request.files.get('original_file')
        corrected_file = request.files.get('corrected_file')

        if original_file and corrected_file:
            original_content = original_file.stream.read().decode("utf-8")
            corrected_content = corrected_file.stream.read().decode("utf-8")

            original_io = io.StringIO(original_content)
            corrected_io = io.StringIO(corrected_content)

            original_reader = list(csv.reader(original_io))
            corrected_reader = list(csv.reader(corrected_io))

            headers = original_reader[0] if original_reader else []
            header_corrected = corrected_reader[0] if corrected_reader else []


            original_data = {row[0]: row for row in original_reader[1:]}
            corrected_data = {row[0]: row for row in corrected_reader[1:]}

            diff = []
            all_keys = set(original_data.keys()) | set(corrected_data.keys())

            for key in sorted(list(all_keys)):
                original_row = original_data.get(key)
                corrected_row = corrected_data.get(key)
                status = ''

                if original_row and not corrected_row:
                    status = 'supprimée'
                    corrected_row = [''] * len(original_row)
                elif not original_row and corrected_row:
                    status = 'ajoutée'
                    original_row = [''] * len(corrected_row)
                elif original_row == corrected_row:
                    status = 'inchangée'
                else:
                    status = 'modifiée'

                diff.append({
                    'original': original_row,
                    'corrected': corrected_row,
                    'status': status
                })

            return render_template('results.html', diff=diff, headers=headers, header_corrected=header_corrected)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
