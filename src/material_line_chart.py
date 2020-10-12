
import datetime


TEMPLATE1 = '''<html>
  <head>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['line']});
      google.charts.setOnLoadCallback(drawChart);

      function drawChart() {

      var data = new google.visualization.DataTable();
'''

TEMPLATE2 ='''
      var chart = new google.charts.Line(document.getElementById('linechart_material'));

      chart.draw(data, google.charts.Line.convertOptions(options));
    }
    </script>
  </head>
  <body>
'''
TEMPLATE3 = '''
    <div id="linechart_material" style="width: {}px; height: {}px"></div>
  </body>
</html>
'''


def _encode_item(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return f'new Date({obj.year}, {obj.month - 1}, {obj.day})'
    elif isinstance(obj, (int, float)):
        return str(obj)
    else:
        return '"' + str(obj) + '"'
        

def _encode_table(data_table):
    table_str = '['
    for row in data_table:
        row_str = '['
        for item in row:
            row_str += _encode_item(item) + ','
        row_str += '],\n'
        table_str += row_str
    table_str += ']'
    return table_str


def create_material_line_char_html(columns, data_table, title, width=900, height=500):
    cols_js = ''
    for col in columns:
        cols_js += f'data.addColumn("{col[0]}", "{col[1]}");\n'

    data_table_js = 'data.addRows(' + _encode_table(data_table) + ');\n'

    options_js = '''var options = {
        chart: {
          title: "''' + title + '"},\n      width: ' + str(width) + ',\n     height: ' + str(height) + '};'
    html = TEMPLATE1 + cols_js + data_table_js + options_js + TEMPLATE2
    html += TEMPLATE3.format(width, height)
    return html


def create_chart_js(js_function_name, div_id, title, columns, data_table, width=600, height=400):
    html = f'google.charts.setOnLoadCallback({js_function_name});\n'
    data_var_name = js_function_name + 'Data'
    char_var_name = js_function_name + 'Chart'
    html += 'function ' + js_function_name + '() {'
    html += f'var {data_var_name} = new google.visualization.DataTable();\n'''
    
    cols_js = ''
    for col in columns:
        cols_js += f'{data_var_name}.addColumn("{col[0]}", "{col[1]}");\n'

    data_table_js = f'{data_var_name}.addRows(' + _encode_table(data_table) + ');\n'

    options_js = '''var options = {
        chart: {
          title: "''' + title + '"},\n      width: ' + str(width) + ',\n     height: ' + str(height) + '};\n'

    html = html + cols_js + data_table_js + options_js

    html += f"var {char_var_name} = new google.charts.Line(document.getElementById('{div_id}'));\n"
    html += f'{char_var_name}.draw({data_var_name}, google.charts.Line.convertOptions(options));\n'
    html += '};\n\n'
    return html


if __name__ == '__main__':
    columns = [('number', 'X'), ('number', 'Y')]
    rows = [[1, 2], [2, 4], [3, 8]]

    create_material_line_char_html(columns=columns, data_table=rows, title='test', width=600, height=400)
